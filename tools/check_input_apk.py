"""Run the compiled ARM32 input and APK check with modeled OS/JNI/crypto APIs."""

import argparse
import hashlib
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm_const as R
from arm32 import Arm32
from check_kuser import ROOT, PAYLOAD, SCRATCH, STOP, STACK, load, put, word, check

REGS = [R.UC_ARM_REG_R0, R.UC_ARM_REG_R1, R.UC_ARM_REG_R2, R.UC_ARM_REG_R3]
DATA = SCRATCH + 0x100000


class Host:
    def __init__(self):
        self.raw = (ROOT / "finn32.elf").read_bytes()
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.syms = {
            s.name: s for s in self.elf.get_section_by_name(".symtab").iter_symbols() if s.name
        }
        self.cpu = u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.ctl_set_cpu_model(R.UC_CPU_ARM_MAX)
        u.mem_map(SCRATCH, 0x10000)
        u.mem_map(DATA, 0x20000)
        load(u, self.elf, PAYLOAD)
        for x in self.elf.get_section_by_name(".rel.dyn").iter_relocations():
            check(x["r_info_type"] == 23, "Unexpected payload relocation")
            a = PAYLOAD + x["r_offset"]
            put(u, a, word(u, a) + PAYLOAD)
        self.hook("debugPrintf", lambda: self.ret())

    def addr(self, n):
        return PAYLOAD + self.syms[n]["st_value"]

    def reg(self, n):
        return self.cpu.reg_read(REGS[n])

    def hook(self, n, fn):
        a = self.addr(n) if isinstance(n, str) else n
        self.cpu.hook_add(UC_HOOK_CODE, lambda u, a, s, d: fn(), begin=a, end=a)

    def ret(self, v=0):
        self.cpu.reg_write(R.UC_ARM_REG_R0, v & 0xFFFFFFFF)
        self.cpu.reg_write(R.UC_ARM_REG_PC, self.cpu.reg_read(R.UC_ARM_REG_LR))

    def string(self, p):
        s = b""
        while (b := bytes(self.cpu.mem_read(p, 1))) != b"\0":
            s += b
            p += 1
        return s.decode()

    def call(self, name, *args):
        u = self.cpu
        u.reg_write(R.UC_ARM_REG_CPSR, 0x10)
        u.reg_write(R.UC_ARM_REG_FPEXC, 0x40000000)
        u.reg_write(R.UC_ARM_REG_SP, STACK)
        u.reg_write(R.UC_ARM_REG_LR, STOP)
        for r, v in zip(REGS, args):
            u.reg_write(r, v)
        u.emu_start(self.addr(name), STOP, count=1000000)
        check(u.reg_read(R.UC_ARM_REG_PC) == STOP, "ARM routine failed to return")
        return self.reg(0)


def input_check():
    h = Host()
    u = h.cpu
    events = []
    masks = []
    buttons = 0
    pulse = 0
    kind = ""
    tick = 0
    size = [1280, 720]
    stick = [0, 0]
    captures = []
    put(u, h.addr("inject"), SCRATCH + 0x200)

    def pad():
        # PadState is libnx32's ABI: buttons_cur u64 at offset 16.
        u.mem_write(h.reg(0) + 16, struct.pack("<Q", buttons))
        u.mem_write(h.reg(0) + 32, struct.pack("<ii", *stick))
        h.ret()

    h.hook("padUpdate", pad)
    h.hook("hidGetTouchScreenStates", lambda: h.ret(0))

    def dimensions():
        put(u, h.reg(0), size[0])
        put(u, h.reg(1), size[1])
        h.ret()

    h.hook("dcr_window_size", dimensions)

    def controls():
        masks.append((h.reg(0), h.reg(1)))
        h.ret(pulse)

    h.hook("finn_controls_tick", controls)

    def obj():
        nonlocal kind
        kind = h.string(h.reg(0))
        h.ret(SCRATCH + 0x3000)

    h.hook("jni_new", obj)
    for n in ("jni_release", "jni_release_obtained"):
        h.hook(n, lambda: h.ret())

    def capture():
        captures.append(True)
        h.ret()

    if "dcr_gl_request_capture" in h.syms:
        h.hook("dcr_gl_request_capture", capture)

    def clock():
        u.reg_write(R.UC_ARM_REG_R1, 0)
        h.ret(1000000000)

    h.hook("dcr_monotonic_ns", clock)

    def inject():
        p = word(u, h.reg(2) + 28)
        if kind.endswith("MotionEvent"):
            events.append(
                (
                    "touch",
                    word(u, p),
                    *struct.unpack("<f", u.mem_read(p + 48, 4)),
                    *struct.unpack("<f", u.mem_read(p + 88, 4)),
                )
            )
        else:
            events.append(("key", word(u, p), word(u, p + 4)))
        h.ret(1)

    h.hook(SCRATCH + 0x200, inject)
    # Replace only the hardware counter read inside the real compiled poller.
    engine = Arm32(str(ROOT / "finn32.elf"))
    engine.arm.skipdata = True
    s = h.syms["dcr_input_frame"]
    text = h.elf.get_section_by_name(".text")
    code = text.data()[
        s["st_value"] - text["sh_addr"] : s["st_value"] - text["sh_addr"] + s["st_size"]
    ]
    for ins in engine.arm.disasm(code, h.addr("dcr_input_frame")):
        if ins.mnemonic != "mrrc":
            continue
        operands = [x.strip() for x in ins.op_str.split(",")]
        lo = getattr(R, "UC_ARM_REG_" + operands[2].upper())
        hi = getattr(R, "UC_ARM_REG_" + operands[3].upper())

        def counter(lo=lo, hi=hi, pc=ins.address):
            nonlocal tick
            tick += 320000
            u.reg_write(lo, tick)
            u.reg_write(hi, 0)
            u.reg_write(R.UC_ARM_REG_PC, pc + 4)

        h.hook(ins.address, counter)

    def frame(b, p=0):
        nonlocal buttons, pulse
        buttons = b
        pulse = p
        h.call("dcr_input_frame")

    frame(2, 1)
    frame(2, 0)
    check([e[1] for e in events] == [0, 1], "B pulse must produce down/up on separate frames")
    check(events[0][2:] == events[1][2:], "B release moved the touch")
    check(masks[0] == (4, 4) and masks[1] == (0, 4), "B press/hold masks wrong")
    frame(0)
    events.clear()
    for bits, want in [(8, 1), (4, 2), (64, 8), (256, 8), (128, 16), (512, 16), (2048, 32)]:
        frame(bits)
        check(masks[-1] == (want, want), "Wrong action mapping")
        frame(0)
    check(not events, "Action buttons injected unintended pointer/key events")
    frame(32)
    frame(0)
    check(events == [("key", 0, 4), ("key", 1, 4)], "Android Back missing on R-stick click")
    events.clear()
    frame(1)
    frame(1)
    frame(0)
    check([e[1] for e in events] == [0, 2, 1], "A drag lifecycle wrong")
    events.clear()
    size[:] = 1920, 1080
    frame(2, 1)
    frame(0)
    check(
        events[0][2] == 960 and abs(events[0][3] - 324) < 0.001, "Dock touch coordinates not scaled"
    )
    events.clear()
    frame(1)
    h.call("finn_input_cancel")
    check([e[1] for e in events] == [0, 3], "Focus loss did not cancel touch")
    events.clear()
    frame(1)
    frame(1 | 2048)
    frame(1 | 2048)
    frame(0)
    check([e[1] for e in events] == [0, 3], "Restart did not cancel a held pointer click")
    check(masks[-3:] == [(32, 32), (0, 32), (0, 0)], "Minus press repeated instead of holding")
    check(not captures, "Minus still requested a blocking screenshot")

    # Moving the stick shows the cursor; any physical button except A hides it.
    def visible():
        return word(u, h.addr("cursor_visible"))

    for bit in list(range(1, 16)) + list(range(24, 35)):
        stick[:] = 32767, 0
        frame(1 << 18)
        check(visible(), "Analog pseudo-button hid the cursor")
        frame(1)
        check(visible(), "A hid the pointer while clicking")
        frame(1 << bit)
        check(not visible(), "Physical button failed to hide cursor: " + str(bit))
        frame(1 << bit)
        check(not visible(), "Held action let the cursor reappear")
        stick[:] = 0, 0
        frame(0)
        check(not visible(), "Cursor reappeared without stick movement")
    stick[:] = 0, 0
    h.call("finn_input_cancel")
    before = len(masks)
    frame(64 | 128 | 1024)
    check(
        len(masks) == before and word(u, h.addr("g_dcr_quit_requested")) == 1,
        "Exit shortcut also triggered penguins",
    )
    return {
        "status": "passed",
        "checks": [
            "all requested button masks",
            "separate down/up",
            "A drag",
            "R-stick Back",
            "1920x1080 touch coordinates",
            "focus cancellation",
            "minus restart press/hold and touch cancellation",
            "minus never captures a frame",
            "all physical buttons except A hide cursor",
            "analog movement shows cursor",
            "exit chord does not click enemies",
        ],
    }


def apk_check(apk):
    h = Host()
    u = h.cpu
    source = apk.read_bytes()
    stream = None
    ctx = None
    fail_read = False
    path = SCRATCH + 0x4000

    def opened():
        nonlocal stream
        stream = io.BytesIO(source)
        # newlib inlines ferror() as a read of FILE's flags at offset 12.
        u.mem_write(SCRATCH + 0x700C, struct.pack("<H", 0x40 if fail_read else 0))
        h.ret(SCRATCH + 0x7000)

    h.hook("fopen", opened)
    h.hook("malloc", lambda: h.ret(DATA))
    h.hook("free", lambda: h.ret())

    def read():
        b = stream.read(h.reg(1) * h.reg(2))
        u.mem_write(h.reg(0), b)
        h.ret(len(b))

    h.hook("fread", read)
    h.hook("ferror", lambda: h.ret(int(fail_read)))
    h.hook("fclose", lambda: h.ret())

    def start():
        nonlocal ctx
        ctx = hashlib.sha256()
        h.ret()

    h.hook("sha256ContextCreate", start)

    def update():
        ctx.update(bytes(u.mem_read(h.reg(1), h.reg(2))))
        h.ret()

    h.hook("sha256ContextUpdate", update)

    def finish():
        u.mem_write(h.reg(1), ctx.digest())
        h.ret()

    h.hook("sha256ContextGetHash", finish)

    def fmt():
        check(h.string(h.reg(1)) == "%02x", "Unexpected digest formatting")
        u.mem_write(h.reg(0), ("%02x" % h.reg(2)).encode() + b"\0")
        h.ret(2)

    h.hook("sprintf", fmt)
    cases = []
    for name in ("cualquier nombre.apk", "FINN.APK"):
        u.mem_write(path, name.encode() + b"\0")
        check(h.call("port_apk_check", path) == 1, "Valid renamed APK rejected")
        cases.append(name)
    changed = bytearray(source)
    changed[100] ^= 1
    source = bytes(changed)
    check(h.call("port_apk_check", path) == 0, "One-byte corruption accepted")
    source = apk.read_bytes()[:-1]
    check(h.call("port_apk_check", path) == 0, "Truncated APK accepted")
    source = apk.read_bytes()
    fail_read = True
    check(h.call("port_apk_check", path) == 0, "Read error accepted")
    return {
        "status": "passed",
        "accepted_names": cases,
        "rejected": ["one-byte change", "truncation", "read error"],
        "limits": "Compiled ARM validation/read loop; file I/O and libnx SHA-256 modeled with Python SHA-256.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apk", type=__import__("pathlib").Path)
    a = ap.parse_args()
    report = {
        "payload_elf_sha256": hashlib.sha256((ROOT / "finn32.elf").read_bytes()).hexdigest(),
        "input": input_check(),
        "apk": apk_check(a.apk),
        "limits": "OS/JNI/crypto boundaries modeled; requires Switch testing.",
    }
    (ROOT / "build/input-apk-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
