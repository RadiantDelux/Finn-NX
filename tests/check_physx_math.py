"""Execute Finn's original PhysX finite-pose check with old/new ARM shims.

Bionic's ABI constants are from AOSP android-4.3_r1/libm/include/math.h.
No PhysX code is changed: the only bound import is __fpclassifyf.
Requires the dev packages used by check_kuser.py. No OS/GPU simulation.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0,
    UC_ARM_REG_SP,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_CPSR,
    UC_ARM_REG_FPEXC,
    UC_ARM_REG_FPSCR,
    UC_CPU_ARM_MAX,
)
from tests.arm32 import Arm32
from tests.check_kuser import ROOT, PAYLOAD, GAME, SCRATCH, STOP, STACK, load, put, word, check


class ArmMath:
    def __init__(self, path, engine):
        self.raw = path.read_bytes()
        elf = ELFFile(io.BytesIO(self.raw))
        symbols = {
            s.name: s["st_value"]
            for s in elf.get_section_by_name(".symtab").iter_symbols()
            if s.name
        }
        self.fn = PAYLOAD + symbols["b___fpclassifyf"]
        self.cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.cpu.ctl_set_cpu_model(UC_CPU_ARM_MAX)
        self.cpu.mem_map(SCRATCH, 0x10000)
        load(self.cpu, elf, PAYLOAD)
        load(self.cpu, engine.e, GAME)
        for r in elf.get_section_by_name(".rel.dyn").iter_relocations():
            check(r["r_info_type"] == 23, "Unexpected payload relocation")
            a = PAYLOAD + r["r_offset"]
            put(self.cpu, a, word(self.cpu, a) + PAYLOAD)
        site = next(a for a, n in engine.plt.items() if n == "__fpclassifyf")
        self.cpu.hook_add(
            UC_HOOK_CODE,
            lambda uc, a, size, data: uc.reg_write(UC_ARM_REG_PC, self.fn),
            begin=GAME + site,
            end=GAME + site,
        )

    def call(self, address, value, fpscr=0):
        uc = self.cpu
        uc.reg_write(UC_ARM_REG_CPSR, 0x10)
        uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        uc.reg_write(UC_ARM_REG_FPSCR, fpscr)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.emu_start(address, STOP, count=100000)
        check(uc.reg_read(UC_ARM_REG_PC) == STOP, "ARM math routine did not return")
        return uc.reg_read(UC_ARM_REG_R0)

    def scalar(self, bits, fpscr=0):
        return self.call(self.fn, bits, fpscr)

    def pose(self, values):
        address = SCRATCH + 0x2000
        self.cpu.mem_write(address, struct.pack("<12I", *values))
        # This is the APK's 12-float finite check called by createActor.
        return self.call(GAME + 0x5E2858, address)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("unity", type=Path)
    ap.add_argument("--baseline", type=Path)
    args = ap.parse_args()
    engine = Arm32(str(args.unity))
    old = ArmMath(args.baseline, engine) if args.baseline else None
    new = ArmMath(ROOT / "finn32.elf", engine)
    cases = [
        ("positive zero", 0x00000000, 0x10),
        ("negative zero", 0x80000000, 0x10),
        ("positive one", 0x3F800000, 4),
        ("negative one", 0xBF800000, 4),
        ("minimum normal", 0x00800000, 4),
        ("maximum finite", 0x7F7FFFFF, 4),
        ("minimum subnormal", 0x00000001, 8),
        ("maximum subnormal", 0x007FFFFF, 8),
        ("negative subnormal", 0x80000001, 8),
        ("positive infinity", 0x7F800000, 1),
        ("negative infinity", 0xFF800000, 1),
        ("quiet NaN", 0x7FC00000, 2),
        ("signaling NaN", 0x7F800001, 2),
        ("negative NaN", 0xFFC01234, 2),
    ]
    if old:
        check(old.scalar(0) == 2 and old.scalar(0x7FC00000) == 0, "Old ABI defect not reproduced")
    for mode in (0, 1 << 24, 3 << 22):  # normal, flush-to-zero, directed rounding
        for label, bits, expected in cases:
            check(
                new.scalar(bits, mode) == expected,
                f"Bionic classification failed: {label}, FPSCR={mode:x}",
            )
    one = 0x3F800000
    identity = [one, 0, 0, 0, one, 0, 0, 0, one, 0, 0, 0]
    old_identity = old.pose(identity) if old else None
    new_identity = new.pose(identity)
    check(
        (old_identity is None or old_identity == 0) and new_identity == 1,
        "Original PhysX identity-pose rejection not corrected",
    )
    pose_cases = [("identity", identity, 1), ("finite nonzero", [one] * 12, 1)]
    for name, bits, expected in [
        ("negative zero", 0x80000000, 1),
        ("subnormal", 1, 1),
        ("infinity", 0x7F800000, 0),
        ("negative infinity", 0xFF800000, 0),
        ("quiet NaN", 0x7FC00000, 0),
        ("signaling NaN", 0x7F800001, 0),
    ]:
        pose_cases.append((name, [one] * 11 + [bits], expected))
    for name, pose, expected in pose_cases:
        check(new.pose(pose) == expected, "Original PhysX finite-pose check failed: " + name)
    if old:
        check(
            old.pose([one] * 11 + [0x7FC00000]) == 1, "Old false acceptance of NaN not reproduced"
        )
    report = {
        "status": "passed",
        "payload_elf_sha256": hashlib.sha256(new.raw).hexdigest(),
        "baseline_0_1_3_elf_sha256": hashlib.sha256(old.raw).hexdigest() if old else None,
        "unity_sha256": hashlib.sha256(engine.raw).hexdigest(),
        "bionic_abi_source": "https://raw.githubusercontent.com/aosp-mirror/platform_bionic/android-4.3_r1/libm/include/math.h",
        "scalar_cases": len(cases),
        "fpscr_modes": 3,
        "original_physx_pose_cases": len(pose_cases),
        "old_identity_finite": old_identity,
        "corrected_identity_finite": new_identity,
        "old_nan_pose_finite": 1 if old else None,
        "corrected_nan_pose_finite": 0,
        "limits": "Actual ARM classification and PhysX finite checks; complete scene creation/gameplay needs Switch testing.",
    }
    (ROOT / "build/physx-math-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
