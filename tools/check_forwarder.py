"""Validate forwarder formats and run the ARM64 installer against modeled services.

No real content storage is touched. SPL uses an artificial test key; AES-XTS
and SHA are modeled with cryptography/hashlib, then independently verified.
"""

import hashlib
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm64_const as R
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from check_kuser import ROOT, load, check
from build_forwarder import TITLE_ID

BASE, TEMP, HEAP = 0x10000000, 0x40000000, 0x50000000
STOP, STACK = TEMP + 0x1000, TEMP + 0xF000
KEY = bytes(range(32))


def digest(b):
    return hashlib.sha256(b).digest()


def u32(b, p):
    return struct.unpack_from("<I", b, p)[0]


def u64(b, p):
    return struct.unpack_from("<Q", b, p)[0]


def pfs(b):
    check(b[:4] == b"PFS0", "PFS magic")
    n = u32(b, 4)
    names = 16 + n * 24
    start = names + u32(b, 8)
    out = {}
    for i in range(n):
        off, size, name, _ = struct.unpack_from("<QQII", b, 16 + i * 24)
        name = b[names + name : b.index(0, names + name)].decode()
        check(start + off + size <= len(b), "PFS bounds")
        out[name] = b[start + off : start + off + size]
    return out


def romfs(b):
    h = struct.unpack_from("<10Q", b)
    check(h[0] == 80, "RomFS header")
    off = u32(b, h[3] + 12)
    out = {}
    seen = set()
    while off != 0xFFFFFFFF:
        check(off not in seen, "RomFS cycle")
        seen.add(off)
        a = h[7] + off
        parent, next_, data, size, chain, nlen = struct.unpack_from("<IIQQII", b, a)
        name = b[a + 32 : a + 32 + nlen].decode()
        check(parent == 0 and h[9] + data + size <= len(b), "RomFS file bounds")
        out[name] = b[h[9] + data : h[9] + data + size]
        off = next_
    return out


def verify_nca(b):
    check(
        b[0x200:0x204] == b"NCA3" and u64(b, 0x208) == len(b) and u64(b, 0x210) == TITLE_ID,
        "NCA identity",
    )
    sections = []
    for i in range(4):
        start, end = struct.unpack_from("<II", b, 0x240 + i * 16)
        if not start:
            continue
        fs = b[0x400 + i * 512 : 0x600 + i * 512]
        data = b[start * 512 : end * 512]
        check(digest(fs) == b[0x280 + i * 32 : 0x2A0 + i * 32], "FS header hash")
        check(fs[4] == 1 and struct.unpack_from("<H", fs)[0] == 2, "FS crypto/version")
        if fs[3] == 2:
            block = u32(fs, 0x28)
            hashoff, hashsize, poff, psize = struct.unpack_from("<4Q", fs, 0x30)
            hashes = data[hashoff : hashoff + hashsize]
            payload = data[poff : poff + psize]
            check(digest(hashes) == fs[8:40], "PFS master hash")
            check(
                hashes
                == b"".join(digest(payload[j : j + block]) for j in range(0, len(payload), block)),
                "PFS block hashes",
            )
            sections.append(pfs(payload))
        elif fs[3] == 3:
            check(fs[8:12] == b"IVFC" and u32(fs, 20) == 7, "IVFC header")
            levels = [struct.unpack_from("<QQII", fs, 24 + j * 24) for j in range(6)]
            first = data[levels[0][0] : levels[0][0] + levels[0][1]]
            check(digest(first) == fs[0xC8:0xE8], "IVFC master hash")
            for j in range(1, 6):
                off, size, log, _ = levels[j]
                po, ps, _, _ = levels[j - 1]
                table = data[po : po + ps]
                block = 1 << log
                for k in range((size + block - 1) // block):
                    chunk = data[off + k * block : off + (k + 1) * block]
                    check(digest(chunk) == table[k * 32 : k * 32 + 32], "IVFC child hash")
            off, size, _, _ = levels[5]
            sections.append(romfs(data[off : off + size]))
        else:
            raise RuntimeError("Unknown FS hash type")
    return sections


def decrypt(b):
    out = bytearray(b)
    for i in range(6):
        c = Cipher(algorithms.AES(KEY), modes.XTS(i.to_bytes(16, "big"))).decryptor()
        out[i * 512 : (i + 1) * 512] = c.update(b[i * 512 : (i + 1) * 512]) + c.finalize()
    return bytes(out)


class Installer:
    def __init__(self, fail="", collision=False, files=None):
        self.fail = fail
        self.collision = collision
        self.files = {} if files is None else files
        for name in ("program", "control", "meta"):
            self.files.setdefault(
                "romfs:/finn-auto-" + name + ".nca",
                (ROOT / ("launcher/romfs/finn-auto-" + name + ".nca")).read_bytes(),
            )
        self.files.setdefault("romfs:/finn32.nsp", (ROOT / "finn32.nsp").read_bytes())
        self.stored = {}
        self.placeholders = {}
        self.metadata = None
        self.published = False
        self.calls = []
        self.streams = {}
        self.heap = HEAP
        self.contexts = {}
        self.raw = (ROOT / "launcher/finn_nx.elf").read_bytes()
        elf = ELFFile(io.BytesIO(self.raw))
        self.syms = {s.name: s for s in elf.get_section_by_name(".symtab").iter_symbols() if s.name}
        self.cpu = u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        u.mem_map(TEMP, 0x10000)
        u.mem_map(HEAP, 0x4000000)
        load(u, elf, BASE)
        for sec in elf.iter_sections():
            if sec["sh_type"] == "SHT_RELR":
                for r in sec.iter_relocations():
                    a = BASE + r["r_offset"]
                    self.put(a, self.qword(a) + BASE)
        for name in (
            "printf",
            "puts",
            "fprintf",
            "consoleUpdate",
            "free",
            "ncmContentStorageClose",
            "ncmContentMetaDatabaseClose",
            "serviceClose",
            "nsExit",
            "ncmExit",
            "splCryptoExit",
        ):
            if name in self.syms:
                self.hook(name, lambda: self.ret())
        self.hook("__syscall_getreent", lambda: self.ret(self.qword(self.addr("_impure_ptr"))))
        self.hook("malloc", lambda: self.ret(self.alloc(self.reg(0))))
        self.hook("calloc", lambda: self.ret(self.alloc(self.reg(0) * self.reg(1))))
        self.hook("fopen", self.fopen)
        self.hook("fread", self.fread)
        self.hook("fwrite", self.fwrite)
        self.hook("fclose", self.fclose)
        self.hook("fseek", self.fseek)
        self.hook("ftell", lambda: self.ret(self.streams[self.reg(0)][0].tell()))
        self.hook("fflush", lambda: self.ret())
        self.hook("stat", lambda: self.ret(0 if self.text(self.reg(0)) in self.files else -1))
        self.hook("mkdir", lambda: self.ret())
        self.hook("rename", self.rename)
        self.hook("remove", self.remove)
        for name in (
            "ncmInitialize",
            "nsInitialize",
            "splCryptoInitialize",
            "nsGetApplicationManagerInterface",
            "ncmOpenContentStorage",
            "ncmOpenContentMetaDatabase",
        ):
            self.hook(name, lambda n=name: self.api(n))
        self.hook("splCryptoGenerateAesKek", lambda: self.generate_kek())
        self.hook("splCryptoGenerateAesKey", self.generate_key)
        self.hook("sha256CalculateHash", self.sha)
        self.hook("aes128XtsContextCreate", self.aes_create)
        self.hook("aes128XtsContextResetSector", self.aes_sector)
        self.hook("aes128XtsEncrypt", self.aes_encrypt)
        self.hook("ncmContentMetaDatabaseList", self.list_meta)
        self.hook("ncmContentMetaDatabaseGetContentIdByType", self.get_program)
        self.hook("ncmContentStorageHas", self.has)
        self.hook("ncmContentStorageGeneratePlaceHolderId", self.placeholder_id)
        self.hook("ncmContentStorageCreatePlaceHolder", self.placeholder_create)
        self.hook("ncmContentStorageWritePlaceHolder", self.placeholder_write)
        self.hook("ncmContentStorageFlushPlaceHolder", lambda: self.api("flush"))
        self.hook("ncmContentStorageRegister", self.register)
        self.hook("ncmContentStorageDeletePlaceHolder", self.placeholder_delete)
        self.hook("ncmContentMetaDatabaseSet", self.set_meta)
        self.hook("ncmContentMetaDatabaseCommit", lambda: self.api("commit"))
        self.cpu.reg_write(R.UC_ARM64_REG_TPIDRRO_EL0, TEMP + 0x8000)
        self.hook("svcSendSyncRequest", self.ipc)
        self.hook("svcCloseHandle", lambda: self.ret())

    def addr(self, n):
        return BASE + self.syms[n]["st_value"]

    def reg(self, n):
        return self.cpu.reg_read(getattr(R, "UC_ARM64_REG_X" + str(n)))

    def qword(self, a):
        return u64(self.cpu.mem_read(a, 8), 0)

    def put(self, a, v):
        self.cpu.mem_write(a, struct.pack("<Q", v))

    def text(self, p):
        out = b""
        while (c := bytes(self.cpu.mem_read(p, 1))) != b"\0":
            out += c
            p += 1
        return out.decode()

    def alloc(self, n):
        p = self.heap
        self.heap += (n + 63) & ~63
        self.cpu.mem_write(p, bytes(n))
        return p

    def hook(self, n, fn):
        a = self.addr(n)
        self.cpu.hook_add(UC_HOOK_CODE, lambda u, a, s, d: fn(), begin=a, end=a)

    def ret(self, v=0):
        self.cpu.reg_write(R.UC_ARM64_REG_X0, v & 0xFFFFFFFFFFFFFFFF)
        self.cpu.reg_write(R.UC_ARM64_REG_PC, self.cpu.reg_read(R.UC_ARM64_REG_LR))

    def api(self, name):
        self.calls.append(name)
        if name == "nsGetApplicationManagerInterface":
            self.cpu.mem_write(self.reg(0), struct.pack("<IIIH2x", 99, 1, 0, 0))
        self.ret(123 if self.fail == name else 0)

    def fopen(self):
        p, m = self.text(self.reg(0)), self.text(self.reg(1))
        write = m != "rb"
        if p not in self.files and not write:
            self.ret(0)
            return
        stream = io.BytesIO(self.files.get(p, b"") if m != "wb" else b"")
        if m == "a":
            stream.seek(0, 2)
        handle = TEMP + 0x3000 + len(self.streams) * 0x100
        self.streams[handle] = (stream, p, write)
        self.ret(handle)

    def fread(self):
        b = self.streams[self.reg(3)][0].read(self.reg(1) * self.reg(2))
        self.cpu.mem_write(self.reg(0), b)
        self.ret(len(b) // self.reg(1))

    def fwrite(self):
        if self.fail == "file_write":
            self.ret(0)
            return
        b = bytes(self.cpu.mem_read(self.reg(0), self.reg(1) * self.reg(2)))
        self.streams[self.reg(3)][0].write(b)
        self.ret(self.reg(2))

    def fclose(self):
        s, p, w = self.streams[self.reg(0)]
        if w:
            self.files[p] = s.getvalue()
        self.ret()

    def fseek(self):
        self.streams[self.reg(0)][0].seek(self.reg(1), self.reg(2))
        self.ret()

    def rename(self):
        a, b = self.text(self.reg(0)), self.text(self.reg(1))
        check(b not in self.files, "Attempted overwrite")
        self.files[b] = self.files.pop(a)
        self.ret()

    def remove(self):
        self.files.pop(self.text(self.reg(0)), None)
        self.ret()

    def generate_kek(self):
        self.cpu.mem_write(self.reg(3), b"K" * 16)
        self.api("derive_kek")

    def generate_key(self):
        src = bytes(self.cpu.mem_read(self.reg(1), 16))
        half = 0 if src[0] == 0x5A else 16
        self.cpu.mem_write(self.reg(2), KEY[half : half + 16])
        self.api("derive_key")

    def sha(self):
        self.cpu.mem_write(self.reg(0), digest(bytes(self.cpu.mem_read(self.reg(1), self.reg(2)))))
        self.ret()

    def aes_create(self):
        self.contexts[self.reg(0)] = (
            bytes(self.cpu.mem_read(self.reg(1), 16)) + bytes(self.cpu.mem_read(self.reg(2), 16)),
            0,
        )
        self.ret()

    def aes_sector(self):
        key, _ = self.contexts[self.reg(0)]
        check(self.reg(2) == 1, "Non-Nintendo XTS tweak")
        self.contexts[self.reg(0)] = (key, self.reg(1))
        self.ret()

    def aes_encrypt(self):
        key, sector = self.contexts[self.reg(0)]
        check(key == KEY, "Wrong SPL key halves")
        c = Cipher(algorithms.AES(key), modes.XTS(sector.to_bytes(16, "big"))).encryptor()
        b = c.update(bytes(self.cpu.mem_read(self.reg(2), self.reg(3)))) + c.finalize()
        self.cpu.mem_write(self.reg(1), b)
        self.ret(len(b))

    def list_meta(self):
        check(
            self.reg(6) == TITLE_ID and self.reg(7) == TITLE_ID, "Database queried unrelated title"
        )
        count = int(self.collision or self.metadata is not None)
        self.cpu.mem_write(self.reg(1), struct.pack("<I", count))
        self.cpu.mem_write(self.reg(2), struct.pack("<I", count))
        if count:
            self.cpu.mem_write(self.reg(3), struct.pack("<QIBB2x", TITLE_ID, 0, 0x80, 0))
        self.ret()

    def get_program(self):
        value = b"?" * 16 if self.collision else self.metadata[24 + 24 : 24 + 24 + 16]
        self.cpu.mem_write(self.reg(1), value)
        self.ret()

    def has(self):
        self.cpu.mem_write(
            self.reg(1), bytes([bytes(self.cpu.mem_read(self.reg(2), 16)) in self.stored])
        )
        self.ret()

    def placeholder_id(self):
        value = (len(self.placeholders) + 1).to_bytes(16, "little")
        self.cpu.mem_write(self.reg(1), value)
        self.ret()

    def placeholder_create(self):
        pid = bytes(self.cpu.mem_read(self.reg(2), 16))
        cid = bytes(self.cpu.mem_read(self.reg(1), 16))
        self.placeholders[pid] = (cid, bytearray(self.reg(3)))
        self.ret()

    def placeholder_write(self):
        if self.fail == "content_write":
            self.api("content_write")
            return
        pid = bytes(self.cpu.mem_read(self.reg(1), 16))
        cid, b = self.placeholders[pid]
        off = self.reg(2)
        b[off : off + self.reg(4)] = self.cpu.mem_read(self.reg(3), self.reg(4))
        self.ret()

    def register(self):
        cid = bytes(self.cpu.mem_read(self.reg(1), 16))
        pid = bytes(self.cpu.mem_read(self.reg(2), 16))
        expected, b = self.placeholders.pop(pid)
        check(cid == expected and digest(b)[:16] == cid, "Registered content ID/hash mismatch")
        self.stored[cid] = bytes(b)
        self.api("register")

    def placeholder_delete(self):
        self.placeholders.pop(bytes(self.cpu.mem_read(self.reg(1), 16)), None)
        self.ret()

    def set_meta(self):
        self.metadata = bytes(self.cpu.mem_read(self.reg(2), self.reg(3)))
        check(len(self.metadata) == 96, "NCM metadata size")
        self.api("set_meta")

    def ipc(self):
        tls = TEMP + 0x8000
        b = bytes(self.cpu.mem_read(tls, 256))
        if u32(b, 0) == 2:
            self.ret()
            return  # CMIF closes the owned manager session.
        check(b"SFCI" in b, "Unexpected IPC: " + b[:64].hex() + ", calls=" + str(self.calls))
        at = b.index(b"SFCI")
        cmd = u32(b, at + 8)
        result = 0
        if cmd == 16:
            check(
                b[at + 16] == 3 and u64(b, at + 24) == TITLE_ID,
                "Wrong NS application record identity",
            )
            size, address, flags = struct.unpack_from("<III", b, 8)
            address |= (flags >> 28) << 32
            record = bytes(self.cpu.mem_read(address, size))
            check(
                size == 24
                and u64(record, 0) == TITLE_ID
                and record[12] == 0x80
                and record[16] == 5,
                "Wrong NS storage record",
            )
            check(
                self.metadata is not None and "commit" in self.calls,
                "Published before database commit",
            )
            check(self.override_path in self.files, "Published before ARM32 override")
            if self.fail != "publish":
                self.published = True
            self.calls.append("publish")
            result = 123 if self.fail == "publish" else 0
        else:
            check(cmd == 404, "Unexpected NS command")
        # A non-domain CMIF response with no output handles/objects.
        response = (
            struct.pack("<II", 0, 8) + bytes(8) + struct.pack("<4I", 0x4F434653, 0, result, 0)
        )
        self.cpu.mem_write(tls, response)
        self.ret()

    @property
    def override_path(self):
        return "sdmc:/atmosphere/contents/%016X/exefs.nsp" % TITLE_ID

    def run(self):
        self.heap = HEAP
        u = self.cpu
        u.reg_write(R.UC_ARM64_REG_SP, STACK)
        u.reg_write(R.UC_ARM64_REG_LR, STOP)
        u.reg_write(R.UC_ARM64_REG_X0, TEMP + 0x2000)
        try:
            u.emu_start(self.addr("finn_install_forwarder"), STOP, count=3000000)
        except UcError as e:
            pc = u.reg_read(R.UC_ARM64_REG_PC)
            names = [
                n
                for n, s in self.syms.items()
                if s["st_value"] <= pc - BASE < s["st_value"] + s["st_size"]
            ]
            raise RuntimeError(f"{e}: {pc:x}, {names}, calls={self.calls}") from e
        check(u.reg_read(R.UC_ARM64_REG_PC) == STOP, "Installer did not return")
        return self.reg(0)


def main():
    parsed = {}
    for name in ("program", "control", "meta"):
        parsed[name] = verify_nca(
            (ROOT / ("launcher/romfs/finn-auto-" + name + ".nca")).read_bytes()
        )
    check(parsed["program"][1]["nextNroPath"] == b"/switch/finn_nx/finn_nx.nro", "Forwarder path")
    npdm = parsed["program"][0]["main.npdm"]
    check(npdm[12] & 1 and u64(npdm, u32(npdm, 0x70) + 16) == TITLE_ID, "Forwarder NPDM")
    control_nacp = parsed["control"][0]["control.nacp"]
    check(control_nacp[0x200:0x300].split(b"\0")[0] == b"RadiantDelux", "Forwarder author")
    check(
        parsed["control"][0]["icon_AmericanEnglish.dat"]
        == (ROOT / "launcher/icon.jpg").read_bytes(),
        "Forwarder icon",
    )
    good = Installer()
    check(good.run() == 0 and good.published, "Fresh install failed")
    check(good.qword(TEMP + 0x2000) == TITLE_ID, "Wrong returned title ID")
    for cid, b in good.stored.items():
        verify_nca(decrypt(b))
    cnmt = next(
        iter(
            verify_nca(decrypt(next(b for b in good.stored.values() if decrypt(b)[0x205] == 1)))[
                0
            ].values()
        )
    )
    check(digest(cnmt[:-32]) == cnmt[-32:], "CNMT digest")
    for i in range(2):
        at = 48 + i * 56
        cid = cnmt[at + 32 : at + 48]
        check(
            cid in good.stored and digest(good.stored[cid]) == cnmt[at : at + 32],
            "CNMT content hash",
        )
    out = pfs(good.files[good.override_path])
    n = out["main.npdm"]
    check(not n[12] & 1 and u64(n, u32(n, 0x70) + 16) == TITLE_ID, "ARM32 override identity")
    cases = [
        "template PFS/IVFC hashes",
        "fresh install",
        "encrypted content IDs and CNMT",
        "correct ARM32 override",
    ]
    before = len(good.stored)
    check(good.run() == 0 and len(good.stored) == before, "Repeated install duplicated content")
    cases.append("idempotent repair")
    for failure in (
        "ncmInitialize",
        "derive_kek",
        "content_write",
        "commit",
        "file_write",
        "publish",
    ):
        bad = Installer(fail=failure)
        check(bad.run() != 0 and not bad.published, "Failure was hidden: " + failure)
        check(not bad.placeholders, "Placeholder leaked: " + failure)
        cases.append("failure: " + failure)
    conflict = Installer(collision=True)
    check(
        conflict.run() != 0 and not conflict.stored and not conflict.published,
        "Unrelated title overwritten",
    )
    cases.append("title collision refused")
    other = Installer(files={good.override_path: b"not Finn"})
    check(
        other.run() != 0 and other.files[good.override_path] == b"not Finn",
        "Unrelated override overwritten",
    )
    cases.append("override collision refused")
    broken = Installer()
    key = "romfs:/finn-auto-control.nca"
    b = bytearray(broken.files[key])
    b[-1] ^= 1
    broken.files[key] = b
    check(broken.run() != 0 and not broken.stored, "Damaged template installed")
    cases.append("damaged template refused")
    report = {
        "status": "passed",
        "launcher_elf_sha256": digest(good.raw).hex(),
        "title_id": "%016X" % TITLE_ID,
        "checks": cases,
        "limits": "Actual ARM64 install logic and generated formats; filesystem, SPL/AES/SHA, NCM/NS services modeled. Real HOME install/launch requires Switch testing.",
    }
    (ROOT / "build/forwarder-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
