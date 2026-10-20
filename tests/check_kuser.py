"""Reproduce Finn's 0xffff0fc0 crash using the original ARM instructions.

Runs the compiled loader fix and kuser.S from finn32.elf in Unicorn, then
runs Unity's original atomic decrement. No game library is modified on disk.
Requires pyelftools, capstone and unicorn. This is a CPU regression check,
not a Switch boot, multithreading or GPU test.
"""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_ERR_FETCH_UNMAPPED
from unicorn.arm_const import (
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_R4,
    UC_ARM_REG_R5,
    UC_ARM_REG_R6,
    UC_ARM_REG_R7,
    UC_ARM_REG_R8,
    UC_ARM_REG_R9,
    UC_ARM_REG_R10,
    UC_ARM_REG_R11,
    UC_ARM_REG_R12,
    UC_ARM_REG_SP,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_CPSR,
)

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD, GAME, SCRATCH = 0x10000000, 0x34000000, 0x40000000
STOP, CELL, MODULE, STACK = SCRATCH + 0x1000, SCRATCH + 0x2000, SCRATCH + 0x3000, SCRATCH + 0xE000
DECREMENT, CRASH_LR = 0x8EDEB8, 0x8EDEDC
REGS = [
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_R4,
    UC_ARM_REG_R5,
    UC_ARM_REG_R6,
    UC_ARM_REG_R7,
    UC_ARM_REG_R8,
    UC_ARM_REG_R9,
    UC_ARM_REG_R10,
    UC_ARM_REG_R11,
    UC_ARM_REG_R12,
]


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def word(cpu, address):
    return struct.unpack("<I", cpu.mem_read(address, 4))[0]


def put(cpu, address, value):
    cpu.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))


def load(cpu, elf, base):
    segments = [p for p in elf.iter_segments() if p["p_type"] == "PT_LOAD"]
    end = max(p["p_vaddr"] + p["p_memsz"] for p in segments)
    cpu.mem_map(base, (end + 0xFFF) & ~0xFFF)
    for p in segments:
        cpu.mem_write(base + p["p_vaddr"], p.data())


def module_layout(elf):
    for cu in elf.get_dwarf_info().iter_CUs():
        for die in cu.iter_DIEs():
            name = die.attributes.get("DW_AT_name")
            if die.tag != "DW_TAG_structure_type" or not name or name.value != b"so_module":
                continue
            fields = {
                d.attributes["DW_AT_name"].value.decode(): d.attributes[
                    "DW_AT_data_member_location"
                ].value
                for d in die.iter_children()
                if d.tag == "DW_TAG_member"
            }
            if "phdr" in fields:
                return fields
    raise RuntimeError("so_module layout missing from ELF debug information")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unity", type=Path)
    args = parser.parse_args()
    payload_raw = (ROOT / "finn32.elf").read_bytes()
    unity_raw = args.unity.read_bytes()
    payload = ELFFile(io.BytesIO(payload_raw))
    unity = ELFFile(io.BytesIO(unity_raw))
    symbols = {s.name: s for s in payload.get_section_by_name(".symtab").iter_symbols() if s.name}

    def addr(name):
        return PAYLOAD + symbols[name]["st_value"]

    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(SCRATCH, 0x10000)
    load(cpu, payload, PAYLOAD)
    load(cpu, unity, GAME)
    for r in payload.get_section_by_name(".rel.dyn").iter_relocations():
        check(r["r_info_type"] == 23, "Unexpected payload relocation type")
        site = PAYLOAD + r["r_offset"]
        put(cpu, site, word(cpu, site) + PAYLOAD)

    # Skip only output formatting. Both the rewriting code and atomic helpers
    # execute their actual machine instructions from the linked payload.
    def skip_log(uc, address, size, data):
        uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    cpu.hook_add(UC_HOOK_CODE, skip_log, begin=addr("debugPrintf"), end=addr("debugPrintf"))

    def call(pc, *arguments, flags=0):
        cpu.reg_write(UC_ARM_REG_CPSR, 0x10 | flags)
        for i, reg in enumerate(REGS):
            cpu.reg_write(reg, 0x12340000 + i)
        for reg, value in zip(REGS, arguments):
            cpu.reg_write(reg, value)
        cpu.reg_write(UC_ARM_REG_SP, STACK)
        cpu.reg_write(UC_ARM_REG_LR, STOP)
        cpu.emu_start(pc, STOP, count=30000000)
        check(
            cpu.reg_read(UC_ARM_REG_PC) == STOP,
            f"ARM routine failed to return (PC={cpu.reg_read(UC_ARM_REG_PC):08x})",
        )
        return cpu.reg_read(UC_ARM_REG_R0)

    check(
        bytes(cpu.mem_read(GAME + DECREMENT, 16))
        == bytes.fromhex("f0412de928709fe50050a0e10160a0e1"),
        "Wrong Unity atomic routine",
    )
    put(cpu, CELL, 1)
    try:
        call(GAME + DECREMENT, CELL, 1)
    except UcError as e:
        check(
            e.errno == UC_ERR_FETCH_UNMAPPED
            and cpu.reg_read(UC_ARM_REG_PC) == 0xFFFF0FC0
            and cpu.reg_read(UC_ARM_REG_LR) == GAME + CRASH_LR,
            "Unpatched failure differs from the supplied crash.log",
        )
    else:
        raise RuntimeError("Unpatched Unity unexpectedly succeeded")

    fields = module_layout(payload)
    for name, value in [
        ("load_base", GAME),
        ("load_virtbase", GAME),
        ("state", 0),
        ("phnum", unity.num_segments()),
        ("base_name", CELL + 0x40),
    ]:
        put(cpu, MODULE + fields[name], value)
    cpu.mem_write(CELL + 0x40, b"libunity.so\0")
    check(
        unity["e_phentsize"] == 32 and unity.num_segments() <= 16,
        "Program headers do not fit so_module",
    )
    phstart = unity["e_phoff"]
    cpu.mem_write(MODULE + fields["phdr"], unity_raw[phstart : phstart + unity.num_segments() * 32])
    rewritten = call(addr("so_fix_kuser_helpers"), MODULE)
    check(rewritten == 47, f"Expected 47 rewritten literals, got {rewritten}")
    counts = {0xFFFF0FC0: 0, 0xFFFF0FA0: 0}
    for p in unity.iter_segments():
        if p["p_type"] != "PT_LOAD" or not p["p_flags"] & 1:
            continue
        original = p.data()
        for off in range(0, len(original) - 3, 4):
            old = struct.unpack_from("<I", original, off)[0]
            if old in counts:
                helper = "dcr_kuser_cmpxchg" if old == 0xFFFF0FC0 else "dcr_kuser_memory_barrier"
                check(
                    word(cpu, GAME + p["p_vaddr"] + off) == addr(helper),
                    "Literal was not redirected",
                )
                counts[old] += 1
    check(list(counts.values()) == [43, 4], "Unexpected helper reference counts")
    check(call(addr("so_fix_kuser_helpers"), MODULE) == 0, "Rewriting is not idempotent")

    cases = [
        (1, 1, 0),
        (0, 1, 0xFFFFFFFF),
        (8, 3, 5),
        (0x80000000, 1, 0x7FFFFFFF),
        (0xFFFFFFFF, 0xFFFFFFFF, 0),
    ]
    for old, delta, expected in cases:
        put(cpu, CELL, old)
        result = call(GAME + DECREMENT, CELL, delta)
        check(
            result == expected and word(cpu, CELL) == expected, "Original atomic decrement failed"
        )
        check(cpu.reg_read(UC_ARM_REG_SP) == STACK, "Unity corrupted the stack")
        check(
            all(cpu.reg_read(REGS[i]) == 0x12340000 + i for i in range(4, 12)),
            "Unity corrupted callee-saved registers",
        )

    attempts = []

    def race_once(uc, address, size, data):
        attempts.append(address)
        if len(attempts) == 1:
            put(uc, CELL, 9)

    h = cpu.hook_add(
        UC_HOOK_CODE, race_once, begin=addr("dcr_kuser_cmpxchg"), end=addr("dcr_kuser_cmpxchg")
    )
    put(cpu, CELL, 7)
    check(
        call(GAME + DECREMENT, CELL, 1) == 8 and len(attempts) == 2 and word(cpu, CELL) == 8,
        "Original Unity CAS retry failed",
    )
    cpu.hook_del(h)

    for current, expected_old, new, success in [(5, 5, 9, True), (7, 5, 9, False)]:
        put(cpu, CELL, current)
        result = call(addr("dcr_kuser_cmpxchg"), expected_old, new, CELL)
        check(
            (result == 0) == success and bool(cpu.reg_read(UC_ARM_REG_CPSR) & (1 << 29)) == success,
            "kuser return value / carry flag contract failed",
        )
        check(word(cpu, CELL) == (new if success else current), "CAS wrote the wrong value")
        check(
            cpu.reg_read(UC_ARM_REG_R1) == new
            and cpu.reg_read(UC_ARM_REG_R2) == CELL
            and all(cpu.reg_read(REGS[i]) == 0x12340000 + i for i in range(4, 12)),
            "kuser ABI changed",
        )
    call(addr("dcr_kuser_memory_barrier"), flags=0xA0000000)
    check(
        cpu.reg_read(UC_ARM_REG_CPSR) & 0xF0000000 == 0xA0000000
        and all(cpu.reg_read(reg) == 0x12340000 + i for i, reg in enumerate(REGS)),
        "Barrier changed registers/flags",
    )

    # Prevent the original integration omission from passing this check: the
    # linked port_load must actually call the fix before making code executable.
    port = symbols["port_load"]
    text = next(p for p in payload.iter_segments() if p["p_type"] == "PT_LOAD" and p["p_flags"] & 1)
    start = port["st_value"] - text["p_vaddr"]
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    calls = [
        (i.address, int(i.op_str[1:], 16))
        for i in md.disasm(text.data()[start : start + port["st_size"]], port["st_value"])
        if i.mnemonic == "bl"
    ]
    fix = [site for site, dest in calls if dest == symbols["so_fix_kuser_helpers"]["st_value"]]
    seal = [site for site, dest in calls if dest == symbols["so_finalize"]["st_value"]]
    check(
        fix and seal and max(fix) < min(seal), "port_load does not redirect helpers before sealing"
    )

    report = {
        "status": "passed",
        "payload_elf_sha256": hashlib.sha256(payload_raw).hexdigest(),
        "unity_sha256": hashlib.sha256(unity_raw).hexdigest(),
        "unpatched_fault_pc": "0xffff0fc0",
        "unpatched_fault_lr_rva": hex(CRASH_LR),
        "cmpxchg_literals": 43,
        "barrier_literals": 4,
        "checks": [
            "compiled loader rewrite and idempotence",
            "5 original Unity decrement cases",
            "original Unity CAS retry",
            "kuser register and carry ABI",
            "memory barrier register/flag preservation",
            "compiled port_load call before finalize",
        ],
        "limits": "CPU regression only; complete boot and concurrency require Switch testing",
    }
    (ROOT / "build/kuser-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
