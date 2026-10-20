"""CPU regression for Unity 4.3 resize and EGL config selection.

Executes the original nativeResize, EGL request construction and selector,
plus the compiled port's resize call and guarded patch. EGL is modeled with
seven RGBA8888 depth/stencil profiles; this does not test a real GPU/context.
Requires the dev packages used by check_kuser.py.
"""

import argparse
import hashlib
import io
import json
import math
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_R8,
    UC_ARM_REG_R10,
    UC_ARM_REG_SP,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_CPSR,
    UC_ARM_REG_FPEXC,
    UC_CPU_ARM_MAX,
)
from tests.arm32 import Arm32
from tests.check_kuser import (
    ROOT,
    PAYLOAD,
    GAME,
    SCRATCH,
    STOP,
    STACK,
    MODULE,
    load,
    put,
    word,
    check,
    module_layout,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("unity")
    args = ap.parse_args()
    engine = Arm32(args.unity)
    payload_raw = (ROOT / "finn32.elf").read_bytes()
    payload = ELFFile(io.BytesIO(payload_raw))
    symbols = {s.name: s for s in payload.get_section_by_name(".symtab").iter_symbols() if s.name}

    def host(name):
        return PAYLOAD + symbols[name]["st_value"]

    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.ctl_set_cpu_model(UC_CPU_ARM_MAX)
    cpu.mem_map(SCRATCH, 0x10000)
    load(cpu, payload, PAYLOAD)
    load(cpu, engine.e, GAME)
    for r in payload.get_section_by_name(".rel.dyn").iter_relocations():
        check(r["r_info_type"] == 23, "Unexpected payload relocation")
        a = PAYLOAD + r["r_offset"]
        put(cpu, a, word(cpu, a) + PAYLOAD)
    ds = engine.e.get_section_by_name(".dynsym")
    for section in engine.e.iter_sections():
        if section["sh_type"] != "SHT_REL":
            continue
        for r in section.iter_relocations():
            a = GAME + r["r_offset"]
            t = r["r_info_type"]
            if t == 23:
                put(cpu, a, word(cpu, a) + GAME)
            elif t in (2, 21, 22):
                sym = ds.get_symbol(r["r_info_sym"])
                v = GAME + sym["st_value"] if sym["st_shndx"] != "SHN_UNDEF" else SCRATCH + 0x7000
                put(cpu, a, v + (word(cpu, a) if t == 2 else 0))

    regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
    history = []

    def trace(uc, a, size, data):
        if SCRATCH <= a < SCRATCH + 0x10000 and a != STOP:
            raise RuntimeError(f"Unexpected stack branch {a:08x}: {[hex(x) for x in history]}")
        history.append(a)
        if len(history) > 32:
            del history[0]

    cpu.hook_add(UC_HOOK_CODE, trace)

    def ret(value=0):
        cpu.reg_write(UC_ARM_REG_R0, value & 0xFFFFFFFF)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def hook(address, fn):
        cpu.hook_add(UC_HOOK_CODE, lambda uc, a, size, data: fn(), begin=address, end=address)

    def call(address, *values, stack_values=(), stop=STOP):
        cpu.reg_write(UC_ARM_REG_CPSR, 0x10)
        cpu.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        cpu.reg_write(UC_ARM_REG_SP, STACK)
        cpu.reg_write(UC_ARM_REG_LR, STOP)
        for r, v in zip(regs, values):
            cpu.reg_write(r, v)
        for i, v in enumerate(stack_values):
            put(cpu, STACK + i * 4, v)
        try:
            cpu.emu_start(address, stop, count=200000)
        except UcError as e:
            raise RuntimeError(
                f"{e}, PC={cpu.reg_read(UC_ARM_REG_PC):08x}, recent={[hex(a) for a in history]}"
            ) from e
        check(cpu.reg_read(UC_ARM_REG_PC) == stop, "ARM routine did not return")
        return cpu.reg_read(UC_ARM_REG_R0)

    hook(host("debugPrintf"), lambda: ret())

    def memcmp():
        a, b, n = [cpu.reg_read(r) for r in regs[:3]]
        ret(0 if bytes(cpu.mem_read(a, n)) == bytes(cpu.mem_read(b, n)) else 1)

    hook(host("memcmp"), memcmp)

    # Native JNI exception guards and viewport application are OS/engine
    # boundaries. The original resize arithmetic still executes unchanged.
    hook(GAME + 0x394400, lambda: ret(SCRATCH + 0x5000))
    hook(GAME + 0x38D1D4, lambda: ret())
    hook(GAME + 0x38CEE4, lambda: ret())
    hook(GAME + 0x399E7C, lambda: ret())
    for site, name in engine.plt.items():
        if name == "setjmp":
            hook(GAME + site, lambda: ret())

    def scales():
        return list(struct.unpack("<2f", cpu.mem_read(GAME + 0xA23B6C, 8)))

    call(GAME + 0x399ED0, 0, 0, 1280, 720, stack_values=(1, 0))
    baseline_scale = scales()
    check(
        baseline_scale[0] == 1280 and math.isinf(baseline_scale[1]),
        "Bad resize call not reproduced",
    )
    check(symbols["U"]["st_size"] == 52, "Unexpected Unity lifecycle struct layout")
    put(cpu, host("U") + 40, GAME + 0x399ED0)
    dimensions = [1280, 720]

    def window_size():
        for reg, value in zip(regs, dimensions):
            p = cpu.reg_read(reg)
            if p:
                put(cpu, p, value)
        ret()

    hook(host("dcr_window_size"), window_size)
    resized = []
    for w, h in [(1280, 720), (1920, 1080), (960, 540)]:
        dimensions[:] = w, h
        call(host("finn_apply_window_resize"))
        actual = scales()
        check(actual == [1.0, 1.0], f"Invalid resize scale {actual}")
        resized.append({"dimensions": [w, h], "scale": actual})

    # Run the actual request-building branch that precedes Unity's selector.
    # Both ProjectSettings bytes are zero, matching the APK defaults.
    settings, quality, levels = SCRATCH + 0x6000, SCRATCH + 0x6200, SCRATCH + 0x6400
    hook(GAME + 0x278B90, lambda: ret(settings))
    hook(GAME + 0x278B68, lambda: ret(quality))
    put(cpu, quality + 0x18, levels)

    def request():
        cpu.reg_write(UC_ARM_REG_R8, 2)
        cpu.reg_write(UC_ARM_REG_R10, 1)
        call(GAME + 0x39C23C, stop=GAME + 0x392B74)
        return bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R0), 44))

    old_request = request()
    check(
        struct.unpack("<11I", old_request)[2:6] == (16, 5, 6, 5), "Original RGB565 request differs"
    )
    fields = module_layout(payload)
    for k, v in [
        ("load_base", GAME),
        ("load_virtbase", GAME),
        ("load_size", 0xC00000),
        ("state", 0),
    ]:
        put(cpu, MODULE + fields[k], v)
    # The compiled port performs its own exact instruction guard and writes
    # its one-word patch to the staged module, just as port_load does.
    check(call(host("finn_display_install"), MODULE) == 1, "Guarded display patch failed")
    check(word(cpu, GAME + 0x39C24C) == 0x03A05018, "Display patch wrote the wrong instruction")
    new_request = request()
    check(
        struct.unpack("<11I", new_request)[2:6] == (24, 8, 8, 8),
        "RGB888 fallback request not enabled",
    )

    got = (0x392B90 + engine.u32(0x393118)) & 0xFFFFFFFF
    empty = word(cpu, GAME + got + engine.u32(0x393124)) + 12

    def format_config():
        put(cpu, cpu.reg_read(UC_ARM_REG_R0), empty)
        ret()

    hook(GAME + 0x38FA48, format_config)
    hook(GAME + 0x2DF338, lambda: ret())  # log formatting
    hook(GAME + 0x38DFC8, lambda: ret(15))  # same Android API level as the port
    depths = [(0, 0), (0, 8), (16, 0), (24, 0), (24, 8), (32, 0), (32, 8)]
    error = [0x3000]

    def choose():
        out = cpu.reg_read(UC_ARM_REG_R2)
        cap = cpu.reg_read(UC_ARM_REG_R3)
        count = word(cpu, cpu.reg_read(UC_ARM_REG_SP))
        put(cpu, count, len(depths) if not out else min(cap, len(depths)))
        if out:
            for i in range(min(cap, len(depths))):
                put(cpu, out + 4 * i, 100 + i)
        error[0] = 0x3000
        ret(1)

    def attrib():
        cfg = cpu.reg_read(UC_ARM_REG_R1)
        a = cpu.reg_read(UC_ARM_REG_R2)
        out = cpu.reg_read(UC_ARM_REG_R3)
        depth, stencil = depths[cfg - 100]
        values = {
            0x3020: 32,
            0x3024: 8,
            0x3023: 8,
            0x3022: 8,
            0x3021: 8,
            0x3025: depth,
            0x3026: stencil,
            0x3031: 0,
            0x3032: 0,
            0x302E: 1,
            0x3039: 0,
            0x303A: 1,
            0x3147: 0,
        }
        if a in values:
            put(cpu, out, values[a])
            error[0] = 0x3000
            ret(1)
        else:
            error[0] = 0x3004
            ret()

    def get_error():
        previous = error[0]
        error[0] = 0x3000
        ret(previous)

    for site, name in engine.plt.items():
        if name == "eglChooseConfig":
            hook(GAME + site, choose)
        elif name == "eglGetConfigAttrib":
            hook(GAME + site, attrib)
        elif name == "eglGetError":
            hook(GAME + site, get_error)

    def select(req):
        location = SCRATCH + 0x8000
        cpu.mem_write(location, req)
        return call(GAME + 0x392B74, location)

    rejected = select(old_request)
    chosen = select(new_request)
    check(
        rejected == 0 and 100 <= chosen < 107,
        "Original EGL selector did not accept the corrected request",
    )
    report = {
        "status": "passed",
        "payload_elf_sha256": hashlib.sha256(payload_raw).hexdigest(),
        "unity_sha256": hashlib.sha256(engine.raw).hexdigest(),
        "bad_resize_scale": [baseline_scale[0], "Infinity"],
        "corrected_resize_cases": resized,
        "old_egl_request_bits": 16,
        "corrected_egl_request_bits": 24,
        "old_selector_result": rejected,
        "corrected_selector_result": chosen,
        "limits": "Original CPU code with modeled RGBA8888 EGL profiles; real GPU/context and gameplay pending Switch test.",
    }
    (ROOT / "build/display-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
