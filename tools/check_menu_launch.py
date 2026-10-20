"""Exercise the built ARM64 menu handoff; OS/file services are modeled."""

import hashlib
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import (
    UC_ARM64_REG_X0,
    UC_ARM64_REG_X1,
    UC_ARM64_REG_X2,
    UC_ARM64_REG_X3,
    UC_ARM64_REG_LR,
    UC_ARM64_REG_SP,
    UC_ARM64_REG_PC,
)
from check_kuser import ROOT, load, check
from build_forwarder import TITLE_ID as AUTO_TID

BASE, TEMP, DATA = 0x10000000, 0x40000000, 0x50000000
STOP, STACK = TEMP + 0x1000, TEMP + 0xF000
REGS = [UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3]
TID = 0x05ABCDEF12345678


def override():
    b = bytearray((ROOT / "finn32.nsp").read_bytes())
    n, ss = struct.unpack_from("<II", b, 4)
    names = 16 + n * 24
    start = names + ss
    for i in range(n):
        off, size, name, _ = struct.unpack_from("<QQII", b, 16 + i * 24)
        if b[names + name : b.index(0, names + name)] != b"main.npdm":
            continue
        p = start + off
        aci, acid = (
            struct.unpack_from("<I", b, p + 0x70)[0],
            struct.unpack_from("<I", b, p + 0x78)[0],
        )
        for at in (aci + 0x10, acid + 0x210, acid + 0x218):
            struct.pack_into("<Q", b, p + at, TID)
        return b, p
    raise RuntimeError("NPDM missing")


def scenario(
    files,
    result=0,
    install_result=123,
    existing=True,
    confirmed=True,
    ns_result=0,
    ns_init_result=0,
    elf_path=None,
):
    raw = (elf_path or ROOT / "launcher/finn_nx.elf").read_bytes()
    elf = ELFFile(io.BytesIO(raw))
    syms = {s.name: s for s in elf.get_section_by_name(".symtab").iter_symbols() if s.name}

    def addr(n):
        return BASE + syms[n]["st_value"]

    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(TEMP, 0x10000)
    u.mem_map(DATA, 0x2000000)
    load(u, elf, BASE)
    for section in elf.iter_sections():
        if section["sh_type"] == "SHT_RELR":
            for r in section.iter_relocations():
                a = BASE + r["r_offset"]
                old = struct.unpack("<Q", u.mem_read(a, 8))[0]
                u.mem_write(a, struct.pack("<Q", old + BASE))
        elif section["sh_type"] == "SHT_RELA":
            for r in section.iter_relocations():
                check(r["r_info_type"] == 1027, "Unexpected ARM64 relocation")
                u.mem_write(BASE + r["r_offset"], struct.pack("<Q", BASE + r["r_addend"]))
    streams = {}
    opened = []
    launched = []
    installed = []
    known_titles = {TID} if existing else set()
    results = list(result) if isinstance(result, list) else None

    def reg(i):
        return u.reg_read(REGS[i])

    def text(p):
        out = b""
        while (c := bytes(u.mem_read(p, 1))) != b"\0":
            out += c
            p += 1
        return out.decode()

    def ret(v=0):
        u.reg_write(UC_ARM64_REG_X0, v & 0xFFFFFFFFFFFFFFFF)
        u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))

    def hook(n, fn):
        u.hook_add(UC_HOOK_CODE, lambda uc, a, s, d: fn(), begin=addr(n), end=addr(n))

    for n in ("printf", "puts", "fprintf", "consoleUpdate", "free"):
        hook(n, lambda: ret())
    if "nsIsAnyApplicationEntityInstalled" in syms:
        hook("nsInitialize", lambda: ret(ns_init_result))
        hook("nsExit", lambda: ret())

        def registered():
            u.mem_write(reg(1), bytes([reg(0) in known_titles]))
            ret(ns_result)

        hook("nsIsAnyApplicationEntityInstalled", registered)
    hook(
        "__syscall_getreent",
        lambda: ret(struct.unpack("<Q", u.mem_read(addr("_impure_ptr"), 8))[0]),
    )
    hook("malloc", lambda: ret(DATA))

    def fopen():
        path = text(reg(0))
        opened.append(path)
        if path not in files:
            ret(0)
            return
        handle = TEMP + 0x3000 + len(streams) * 0x100
        streams[handle] = io.BytesIO(files[path])
        ret(handle)

    hook("fopen", fopen)
    hook("fclose", lambda: ret())

    def fread():
        b = streams[reg(3)].read(reg(1) * reg(2))
        u.mem_write(reg(0), b)
        ret(len(b) // reg(1))

    hook("fread", fread)

    def seek():
        streams[reg(0)].seek(reg(1), reg(2))
        ret()

    hook("fseek", seek)
    hook("ftell", lambda: ret(streams[reg(0)].tell()))

    def request():
        launched.append(reg(0))
        ret(results.pop(0) if results is not None else result)

    hook("appletRequestLaunchApplication", request)

    def install():
        installed.append(True)
        if not install_result:
            u.mem_write(reg(0), struct.pack("<Q", AUTO_TID))
            if confirmed:
                known_titles.add(AUTO_TID)
        ret(install_result)

    hook("finn_install_forwarder", install)
    u.reg_write(UC_ARM64_REG_SP, STACK)
    u.reg_write(UC_ARM64_REG_LR, STOP)
    try:
        u.emu_start(addr("port_launcher_open_menu"), STOP, count=1000000)
    except UcError as exc:
        pc = u.reg_read(UC_ARM64_REG_PC)
        names = [
            n for n, s in syms.items() if s["st_value"] <= pc - BASE < s["st_value"] + s["st_size"]
        ]
        raise RuntimeError(f"{exc}, PC={pc:x}, symbols={names}, opened={opened}") from exc
    check(u.reg_read(UC_ARM64_REG_PC) == STOP, "Menu handoff did not return")
    return reg(0), launched, installed


def main():
    valid, npdm = override()
    root = "sdmc:/switch/finn_nx/title_id.txt"
    target = "sdmc:/atmosphere/contents/%016X/exefs.nsp" % TID
    title = ("Finn runs from HOME %016X.\n" % TID).encode()
    rc, ids, installs = scenario({root: title, target: valid})
    check(rc == 1 and ids == [TID] and not installs, "Valid Finn title not reused")
    cases = ["installed Finn launch"]
    for name, files in [
        ("missing title file", {}),
        ("missing override", {root: title}),
        ("system title", {root: b"0100000000001000"}),
        ("malformed override", {root: title, target: b"bad data"}),
    ]:
        rc, ids, installs = scenario(files)
        check(rc == 0 and not ids and installs, "Invalid launch/setup: " + name)
        cases.append(name)
    other = bytearray(valid)
    other[npdm + 0x20 : npdm + 0x26] = b"other\0"
    rc, ids, _ = scenario({root: title, target: other})
    check(not rc and not ids, "Other game launched")
    cases.append("other game rejected")
    wrong = bytearray(valid)
    wrong[npdm + 12] |= 1
    rc, ids, _ = scenario({root: title, target: wrong})
    check(not rc and not ids, "64-bit title accepted")
    cases.append("wrong ABI rejected")
    rc, ids, _ = scenario({root: title, target: valid}, 123)
    check(not rc and ids == [TID], "Launch failure not reported")
    cases.append("OS launch failure")
    rc, ids, installs = scenario({}, install_result=0)
    check(
        rc == 1 and ids == [AUTO_TID] and len(installs) == 1,
        "First-run automatic install/launch failed",
    )
    cases.append("first-run automatic install and launch")
    rc, ids, installs = scenario({root: title, target: valid}, result=[123, 0], install_result=0)
    check(
        rc == 1 and ids == [TID, AUTO_TID] and len(installs) == 1,
        "Failed existing forwarder not recovered",
    )
    cases.append("failed existing forwarder falls back to own installer")
    rc, ids, installs = scenario({}, result=123, install_result=0)
    check(not rc and ids == [AUTO_TID] and installs, "Post-install launch failure hidden")
    cases.append("post-install launch failure reported")
    # HOME can accept a request for a removed title and only fail afterwards.
    # Leftover SD files must never be enough to make that request.
    stale = {root: title, target: valid}
    baseline = ROOT / "build/finn-menu-0.1.8-regression.elf"
    if baseline.exists():
        rc, ids, installs = scenario(stale, existing=False, install_result=0, elf_path=baseline)
        check(
            rc == 1 and ids == [TID] and not installs,
            "Could not reproduce deleted-forwarder bug in 0.1.8",
        )
        cases.append("baseline 0.1.8 reproduces accepted launch of deleted title")
    rc, ids, installs = scenario(stale, existing=False, install_result=0)
    check(
        rc == 1 and ids == [AUTO_TID] and len(installs) == 1,
        "Deleted forwarder was launched instead of reinstalled",
    )
    cases.append("deleted forwarder with intact SD override installs before launch")
    rc, ids, installs = scenario(stale, existing=False)
    check(not rc and not ids and installs, "Failed reinstall still launched a deleted title")
    cases.append("failed reinstall never requests deleted title")
    rc, ids, installs = scenario({}, install_result=0, confirmed=False)
    check(not rc and not ids and installs, "Unconfirmed installation was launched")
    cases.append("new installation must be visible to NS before launch")
    for options in ({"ns_result": 123}, {"ns_init_result": 123}):
        rc, ids, installs = scenario(stale, **options)
        check(not rc and not ids and installs, "Failed system lookup trusted leftover SD files")
    cases.append("NS lookup and initialization failures fail closed")
    report = {
        "status": "passed",
        "launcher_elf_sha256": hashlib.sha256(
            (ROOT / "launcher/finn_nx.elf").read_bytes()
        ).hexdigest(),
        "baseline_0_1_8_elf_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest()
        if baseline.exists()
        else None,
        "checks": cases,
        "limits": "Real compiled ARM64 routing/NPDM validation; filesystem, NS installed-state and application-launch service modeled. Switch handoff pending.",
    }
    (ROOT / "build/menu-launch-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
