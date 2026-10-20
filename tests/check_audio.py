"""Exercise the compiled audio lifecycle and PCM pump with the APK's JNI natives.

FMOD's DSP mixer, thread scheduling and audout service are modeled boundaries.
The real ARM host lifecycle, FMOD JNI wrappers, direct-buffer lookup and
resampling execute. This does not establish audible output on a Switch.
"""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_CPU_ARM_MAX,
    UC_ARM_REG_CPSR,
    UC_ARM_REG_FPEXC,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_SP,
)
from tests.arm32 import Arm32
from tests.check_kuser import ROOT, PAYLOAD, GAME, SCRATCH, STOP, STACK, load, put, word, check

REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]


class Audio:
    def __init__(self, path, engine):
        self.raw = path.read_bytes()
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.syms = {
            s.name: s for s in self.elf.get_section_by_name(".symtab").iter_symbols() if s.name
        }
        self.engine = engine
        self.events = []
        self.thread_fn = 0
        self.create_rc = self.start_rc = 0
        self.mixed = 0
        self.output = []
        self.rate = 24000
        self.frames = 512
        self.cpu = uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.ctl_set_cpu_model(UC_CPU_ARM_MAX)
        uc.mem_map(SCRATCH, 0x10000)
        uc.mem_map(SCRATCH + 0x100000, 0x100000)
        self.heap = SCRATCH + 0x100000
        load(uc, self.elf, PAYLOAD)
        load(uc, engine.e, GAME)
        for r in self.elf.get_section_by_name(".rel.dyn").iter_relocations():
            check(r["r_info_type"] == 23, "Unexpected payload relocation")
            a = PAYLOAD + r["r_offset"]
            put(uc, a, word(uc, a) + PAYLOAD)
        self.hook(self.host("debugPrintf"), lambda: self.ret())
        self.device = self.obj("org/fmod/FMODAudioDevice")
        self.hook(self.host("jni_singleton"), self.singleton)
        self.hook(self.host("jni_new"), lambda: self.ret(self.obj(self.cstr(self.reg(0)))))
        self.hook(self.host("jni_native"), self.native)
        self.hook(self.host("dcr_audio_open"), lambda: self.ret())
        self.hook(self.host("memalign"), lambda: self.ret(self.alloc(self.reg(1))))
        self.hook(self.host("free"), lambda: self.ret())
        self.hook(self.host("threadCreate"), self.create)
        self.hook(self.host("threadStart"), lambda: self.event("threadStart", self.start_rc))
        self.hook(self.host("threadWaitForExit"), lambda: self.event("threadWait"))
        self.hook(self.host("threadClose"), lambda: self.event("threadClose"))
        self.hook(self.host("submit"), self.submit)
        self.hook(self.host("svcSleepThread"), self.sleep)
        # Install the two real JNI operations used by the APK's wrappers.
        put(uc, self.host("g_fn") + 0x36C, self.host("j_GetJavaVM"))
        put(uc, self.host("g_fn") + 0x398, self.host("j_GetDirectBufferAddress"))
        self.hook(GAME + 0x576B64, lambda: self.event("InitFmodJni"))
        # FMOD's internal mixer state and DSP buffer query.
        system = SCRATCH + 0x5000
        inner = SCRATCH + 0x6000
        put(uc, GAME + 0xB83B78, system)
        put(uc, system + 0x30, inner)
        self.inner = inner
        self.hook(GAME + 0x512B14, self.buffer_info)
        self.hook(GAME + 0x568CB0, self.mix)
        self.hook(GAME + 0x572560, lambda: self.ret())
        self.hook(GAME + 0x572484, lambda: self.ret())
        # Hardware counter reads are independent of the PCM path.
        p = self.syms["pump"]
        start = p["st_value"]
        data = self.elf.get_section_by_name(".text")
        code = data.data()[start - data["sh_addr"] : start - data["sh_addr"] + p["st_size"]]
        engine.arm.skipdata = True
        for ins in engine.arm.disasm(code, PAYLOAD + start):
            if ins.mnemonic == "mrrc":
                rs = [x.strip() for x in ins.op_str.split(",")]
                # The compiler chooses two arbitrary ARM registers.
                from unicorn import arm_const

                a = getattr(arm_const, "UC_ARM_REG_" + rs[2].upper())
                b = getattr(arm_const, "UC_ARM_REG_" + rs[3].upper())

                def tick(a=a, b=b, pc=ins.address):
                    uc.reg_write(a, 0)
                    uc.reg_write(b, 0)
                    uc.reg_write(UC_ARM_REG_PC, pc + 4)

                self.hook(ins.address, tick)

    def host(self, name):
        return PAYLOAD + self.syms[name]["st_value"]

    def reg(self, n):
        return self.cpu.reg_read(REGS[n])

    def cstr(self, p):
        out = bytearray()
        while (c := bytes(self.cpu.mem_read(p, 1))) != b"\0":
            out += c
            p += 1
        return out.decode()

    def alloc(self, n):
        p = self.heap
        self.heap += (n + 63) & ~63
        return p

    def obj(self, name):
        p = self.alloc(64)
        c = self.alloc(128)
        self.cpu.mem_write(c, name.encode() + b"\0")
        if name == "java/nio/DirectByteBuffer":
            parent = self.alloc(128)
            self.cpu.mem_write(parent, b"java/nio/ByteBuffer\0")
            put(self.cpu, c + 112, parent)
        put(self.cpu, p, 0x4A4F424A)
        self.cpu.mem_write(p + 5, b"\x01")
        put(self.cpu, p + 8, 1)
        put(self.cpu, p + 12, c)
        return p

    def hook(self, address, fn):
        self.cpu.hook_add(UC_HOOK_CODE, lambda uc, a, size, data: fn(), begin=address, end=address)

    def ret(self, v=0):
        self.cpu.reg_write(UC_ARM_REG_R0, v & 0xFFFFFFFF)
        self.cpu.reg_write(UC_ARM_REG_PC, self.cpu.reg_read(UC_ARM_REG_LR))

    def event(self, name, v=0):
        self.events.append(name)
        self.ret(v)

    def singleton(self):
        check(self.cstr(self.reg(0)) == "org/fmod/FMODAudioDevice", "Wrong audio device class")
        self.ret(self.device)

    def native(self):
        check(self.cstr(self.reg(0)) == "org/fmod/FMODAudioDevice", "Wrong native class")
        name = self.cstr(self.reg(1))
        self.ret(GAME + self.engine.dynsym_def["Java_org_fmod_FMODAudioDevice_" + name])

    def create(self):
        self.thread_fn = self.reg(1)
        self.event("threadCreate", self.create_rc)

    def buffer_info(self):
        if self.reg(1):
            put(self.cpu, self.reg(1), self.frames)
        if self.reg(2):
            put(self.cpu, self.reg(2), 4)
        self.ret()

    def mix(self):
        check(self.reg(2) == self.frames, "FMOD got the wrong block length")
        samples = []
        for i in range(self.frames):
            v = ((self.mixed * self.frames + i) % 1024) * 16 - 8192
            samples.extend((v, -v))
        self.cpu.mem_write(self.reg(1), struct.pack("<" + "h" * len(samples), *samples))
        self.mixed += 1
        self.ret()

    def submit(self):
        self.output.extend(struct.unpack("<2048h", self.cpu.mem_read(self.reg(0), 4096)))
        if len(self.output) >= 8192:
            put(self.cpu, self.host("g_run"), 0)
        self.ret()

    def sleep(self):
        raise RuntimeError("Unexpected audio wait in ready mixer")

    def call(self, name, *args):
        uc = self.cpu
        uc.reg_write(UC_ARM_REG_CPSR, 0x10)
        uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        for r, v in zip(REGS, args):
            uc.reg_write(r, v)
        address = self.host(name) if isinstance(name, str) else name
        try:
            uc.emu_start(address, STOP, count=4000000)
        except UcError as e:
            pc = uc.reg_read(UC_ARM_REG_PC)
            ins = list(self.engine.arm.disasm(bytes(uc.mem_read(pc, 4)), pc))
            raise RuntimeError(f"{e} at {pc:08x}: {[(i.mnemonic, i.op_str) for i in ins]}") from e
        check(uc.reg_read(UC_ARM_REG_PC) == STOP, "ARM audio call did not return")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("unity", type=Path)
    ap.add_argument("--baseline", type=Path)
    args = ap.parse_args()
    engine = Arm32(str(args.unity))
    old = Audio(args.baseline, engine) if args.baseline else None
    if old:
        old.call("port_focus_gained")
        check(not old.events, "Baseline already starts audio")
    results = []
    for rate in (24000, 48000):
        a = Audio(ROOT / "finn32.elf", engine)
        a.rate = rate
        put(a.cpu, a.inner + 0x55C, rate)
        a.call("port_focus_gained")
        check(
            a.events == ["InitFmodJni", "threadCreate", "threadStart"],
            "Audio JNI init/start order wrong",
        )
        a.call("port_focus_gained")
        check(len(a.events) == 3, "Duplicate audio thread started")
        a.call(a.thread_fn, 0)
        check(a.mixed > 0 and len(a.output) >= 8192, "PCM never reached audout boundary")
        for k in range(len(a.output) // 2):
            # Source is a repeating ramp; compute linear interpolation including wrap.
            x = k * rate / 48000
            i = int(x)
            t = x - i
            left = (i % 1024) * 16 - 8192
            right = ((i + 1) % 1024) * 16 - 8192
            want = int(left + (right - left) * t)
            check(
                a.output[2 * k : 2 * k + 2] == [want, -want],
                f"Corrupt stereo PCM at frame {k}, rate {rate}",
            )
        a.call("port_focus_lost")
        check(a.events[-2:] == ["threadWait", "threadClose"], "Exited audio thread was not joined")
        a.call("port_focus_gained")
        check(a.events[-2:] == ["threadCreate", "threadStart"], "Resume did not restart audio")
        a.call("port_focus_lost")
        a.call("port_focus_lost")
        results.append(
            {
                "source_hz": rate,
                "output_hz": 48000,
                "mixed_blocks": a.mixed,
                "verified_stereo_frames": len(a.output) // 2,
            }
        )
    for stage in ("create", "start"):
        a = Audio(ROOT / "finn32.elf", engine)
        setattr(a, stage + "_rc", 1)
        a.call("port_focus_gained")
        check(
            word(a.cpu, a.host("g_run")) == 0 and word(a.cpu, a.host("g_thread_open")) == 0,
            "Failed thread left audio running",
        )
        check(word(a.cpu, a.host("g_device")) == 0, "Failed thread retained device")
        if stage == "start":
            check(a.events[-1] == "threadClose", "Failed start did not close thread")
        setattr(a, stage + "_rc", 0)
        a.call("port_focus_gained")
        check(word(a.cpu, a.host("g_run")) == 1, "Audio cannot retry after thread failure")
    report = {
        "status": "passed",
        "payload_elf_sha256": hashlib.sha256(a.raw).hexdigest(),
        "baseline_0_1_4_elf_sha256": hashlib.sha256(old.raw).hexdigest() if old else None,
        "unity_sha256": hashlib.sha256(engine.raw).hexdigest(),
        "baseline_starts_audio": False if old else None,
        "lifecycle": [
            "initialize",
            "start",
            "duplicate resume",
            "PCM pump exits",
            "pause joins",
            "resume restarts",
            "duplicate pause",
        ],
        "thread_failure_cleanup": ["create", "start"],
        "pcm_cases": results,
        "limits": "Original APK JNI wrappers and compiled host/PCM conversion run; DSP mixing, audout and scheduling modeled. Audible output requires Switch testing.",
    }
    (ROOT / "build/audio-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
