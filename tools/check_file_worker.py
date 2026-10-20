"""Run Unity 4.3's original APK-reader thread against compiled condvar shims.

Compare an old payload with the new one. Unicorn models CPU execution; a
small SVC scheduler supplies one read job after an idle interval. No game
code is patched on disk. Requires the same dev packages as check_kuser.py.
"""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.arm_const import (
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_R4,
    UC_ARM_REG_SP,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_CPSR,
    UC_CPU_ARM_MAX,
)
from arm32 import Arm32
from check_kuser import ROOT, PAYLOAD, GAME, SCRATCH, load, put, word, check

WORKER = 0x38CCCC
JOB, BUFFER, DEQUE, BMUTEX = [SCRATCH + x for x in (0x2000, 0x3000, 0x4000, 0x5000)]
READ_BYTES = b"FINNTEST"


def simulate(payload_path, unity_path):
    raw = payload_path.read_bytes()
    elf = ELFFile(io.BytesIO(raw))
    symbols = {
        s.name: s["st_value"] for s in elf.get_section_by_name(".symtab").iter_symbols() if s.name
    }
    engine = Arm32(str(unity_path))
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.ctl_set_cpu_model(UC_CPU_ARM_MAX)  # ARMv8 AArch32 acquire/release instructions
    cpu.mem_map(SCRATCH, 0x10000)
    load(cpu, elf, PAYLOAD)
    load(cpu, engine.e, GAME)
    for r in elf.get_section_by_name(".rel.dyn").iter_relocations():
        check(r["r_info_type"] == 23, "Unexpected payload relocation")
        target = PAYLOAD + r["r_offset"]
        put(cpu, target, word(cpu, target) + PAYLOAD)

    # Recover the exact globals from this APK's PC-relative literals.
    mutex = GAME + ((0x38AC80 + engine.u32(0x38ACB0)) & 0xFFFFFFFF)
    condition = GAME + ((0x38AC90 + engine.u32(0x38ACB4)) & 0xFFFFFFFF)
    queue = GAME + ((0x38CD04 + engine.u32(0x38CE4C)) & 0xFFFFFFFF)
    put(cpu, mutex, BMUTEX)
    # BMutex: magic, normal type, native mutex, owner, recursion count.
    cpu.mem_write(BMUTEX, struct.pack("<5I", 0x4D555458, 0, 0, 0, 0))
    put(cpu, JOB + 4, 0x1234)  # fake FILE, observed only by the fread boundary
    put(cpu, JOB + 0xC, BUFFER)
    put(cpu, JOB + 0x10, len(READ_BYTES))
    result = {"waits_ns": [], "worker_exited": False, "read_completed": False}

    def ret(value=0):
        cpu.reg_write(UC_ARM_REG_R0, value)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def guest_call(uc, address, size, name):
        if name in (
            "pthread_mutex_lock",
            "pthread_mutex_unlock",
            "pthread_cond_wait",
            "pthread_cond_signal",
        ):
            uc.reg_write(UC_ARM_REG_PC, PAYLOAD + symbols["b_" + name])
        elif name == "pthread_exit":
            result["worker_exited"] = True
            uc.emu_stop()
        elif name == "fread":
            check(
                uc.reg_read(UC_ARM_REG_R0) == BUFFER
                and uc.reg_read(UC_ARM_REG_R1) == 1
                and uc.reg_read(UC_ARM_REG_R2) == len(READ_BYTES)
                and uc.reg_read(UC_ARM_REG_R3) == 0x1234,
                "Unexpected original worker read request",
            )
            uc.mem_write(BUFFER, READ_BYTES)
            ret(len(READ_BYTES))
        else:  # prctl: give this CPU-only thread its original name, no OS needed
            ret()

    for site, name in engine.plt.items():
        if name in (
            "prctl",
            "pthread_mutex_lock",
            "pthread_mutex_unlock",
            "pthread_cond_wait",
            "pthread_cond_signal",
            "pthread_exit",
            "fread",
        ):
            cpu.hook_add(
                UC_HOOK_CODE, guest_call, user_data=name, begin=GAME + site, end=GAME + site
            )
    for name in ("mutexLock", "mutexUnlock"):
        cpu.hook_add(
            UC_HOOK_CODE,
            lambda uc, address, size, data: ret(),
            begin=PAYLOAD + symbols[name],
            end=PAYLOAD + symbols[name],
        )

    def svc(uc, interrupt, data):
        instruction = word(uc, uc.reg_read(UC_ARM_REG_PC) - 4)
        number = instruction & 0xFFFFFF
        address = uc.reg_read(UC_ARM_REG_R0)
        if number == 0x34:
            check(address == condition, f"Unexpected condition address {address:08x}")
            # The same int32 SVC ABI passed this console's startup self-test.
            timeout = (uc.reg_read(UC_ARM_REG_R4) << 32) | uc.reg_read(UC_ARM_REG_R3)
            if timeout & (1 << 63):
                timeout -= 1 << 64
            result["waits_ns"].append(timeout)
            check(len(result["waits_ns"]) == 1, "Worker requested an unexpected second wait")
            if timeout >= 0:
                # Before a job is available, the old shim manufactures a wake
                # by timing out. The original engine then exits its worker.
                uc.reg_write(UC_ARM_REG_R0, 0xEA01)  # Kernel TimedOut
            else:
                # No synthetic deadline: an actual request arrives after an
                # arbitrary idle interval, enqueues the read and signals it.
                put(uc, DEQUE, JOB)
                put(uc, queue + 8, DEQUE)
                put(uc, queue + 0xC, DEQUE)
                put(uc, queue + 0x10, DEQUE + 0x200)
                put(uc, queue + 0x18, DEQUE + 4)
                put(uc, condition, word(uc, condition) + 1)
                uc.reg_write(UC_ARM_REG_R0, 0)
        elif number == 0x35:
            check(address == JOB + 8, "Original worker signaled the wrong request")
            result["read_completed"] = (
                bytes(uc.mem_read(BUFFER, len(READ_BYTES))) == READ_BYTES
                and word(uc, JOB + 0xC) == 0
                and word(uc, JOB + 0x14) == len(READ_BYTES)
            )
            uc.reg_write(UC_ARM_REG_R0, 0)
            uc.emu_stop()
        else:
            raise RuntimeError(f"Unmodeled SVC {number:x}")

    cpu.hook_add(UC_HOOK_INTR, svc)
    cpu.reg_write(UC_ARM_REG_CPSR, 0x10)
    cpu.reg_write(UC_ARM_REG_SP, SCRATCH + 0xE000)
    cpu.reg_write(UC_ARM_REG_LR, SCRATCH + 0x1000)
    try:
        cpu.emu_start(GAME + WORKER, SCRATCH + 0x1000, count=100000)
    except UcError as e:
        pc = cpu.reg_read(UC_ARM_REG_PC)
        raise RuntimeError(f"{e}: PC={pc:08x}, bytes={bytes(cpu.mem_read(pc, 4)).hex()}") from e
    check(
        result["worker_exited"] or result["read_completed"],
        f"Worker stopped unexpectedly at {cpu.reg_read(UC_ARM_REG_PC):08x}",
    )
    return {"elf_sha256": hashlib.sha256(raw).hexdigest(), **result}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("unity", type=Path)
    ap.add_argument("--baseline", type=Path)
    args = ap.parse_args()
    old = simulate(args.baseline, args.unity) if args.baseline else None
    new = simulate(ROOT / "finn32.elf", args.unity)
    if old:
        check(
            old["worker_exited"] and not old["read_completed"] and old["waits_ns"] == [250000000],
            "Baseline does not reproduce the APK worker shutdown",
        )
    check(
        new["read_completed"] and not new["worker_exited"] and new["waits_ns"] == [-1],
        "Updated shim did not keep the APK worker alive and complete its request",
    )
    report = {
        "status": "passed",
        "original_unity_worker_rva": hex(WORKER),
        "unity_sha256": hashlib.sha256(args.unity.read_bytes()).hexdigest(),
        "baseline_0_1_1": old,
        "updated": new,
        "limits": "Original ARM worker and compiled condvars; OS scheduling/file read are modeled. Switch boot pending.",
    }
    (ROOT / "build/file-worker-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
