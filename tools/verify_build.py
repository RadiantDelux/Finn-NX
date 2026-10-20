"""Read back the produced artifacts and compare with their actual inputs.

This checks packaging and ABI selection; it does not claim gameplay testing.
Uses only the Python standard library.
"""

import hashlib
import json
import struct
from pathlib import Path
from tools.licenses import license_notices
from tools.project import VERSION

root = Path(__file__).resolve().parent.parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def elf_segments(data):
    h = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    check(h[0][:6] == b"\x7fELF\x01\x01" and h[2] == 40, "Payload is not ARM ELF32")
    return [
        p for i in range(h[10]) if (p := struct.unpack_from("<8I", data, h[5] + i * h[9]))[0] == 1
    ]


def pfs(data):
    check(data[:4] == b"PFS0", "Bad ExeFS PFS0 magic")
    n, ss = struct.unpack_from("<II", data, 4)
    names = 16 + n * 24
    start = names + ss
    out = {}
    for i in range(n):
        off, size, name, _ = struct.unpack_from("<QQII", data, 16 + i * 24)
        name = data[names + name : data.index(0, names + name)].decode()
        check(start + off + size <= len(data), "PFS0 member outside the file")
        out[name] = data[start + off : start + off + size]
    return out


def romfs(data):
    h = struct.unpack_from("<10Q", data)
    check(h[0] == 0x50, "Bad RomFS header")
    cursor = struct.unpack_from("<I", data, h[3] + 12)[0]
    out = {}
    seen = set()
    while cursor != 0xFFFFFFFF:
        check(cursor not in seen and cursor + 32 <= h[8], "Bad RomFS sibling chain")
        seen.add(cursor)
        pos = h[7] + cursor
        parent, next_, off, size, hash_next, nlen = struct.unpack_from("<IIQQII", data, pos)
        name = data[pos + 32 : pos + 32 + nlen].decode()
        check(h[9] + off + size <= len(data), "RomFS file outside the image")
        out[name] = data[h[9] + off : h[9] + off + size]
        cursor = next_
    return out


elf = (root / "finn32.elf").read_bytes()
nso = (root / "build/finn32.nso").read_bytes()
controls = (root / "build/FinnControls.dll").read_bytes()
check(controls[:2] == b"MZ" and b"v2.0.50727" in controls, "Controls do not target CLR 2")
check(controls in elf, "Managed controls are not embedded in the ARM32 payload")
check(nso[:4] == b"NSO0", "Bad NSO header")
check(struct.unpack_from("<I", nso, 12)[0] == 0x38, "Unexpected NSO compression/hash flags")
segments = elf_segments(elf)
check(len(segments) == 3, "Wrong ELF segment count")
for i, p in enumerate(segments):
    foff, va, size = struct.unpack_from("<III", nso, 0x10 + i * 16)
    body = nso[foff : foff + size]
    check(va == p[2] and size == p[4], "NSO segment layout differs from ELF")
    check(body == elf[p[1] : p[1] + p[4]], "NSO segment bytes differ from ELF")
    check(
        hashlib.sha256(body).digest() == nso[0xA0 + i * 32 : 0xC0 + i * 32],
        "NSO segment hash mismatch",
    )
check(struct.unpack_from("<I", nso, 0x3C)[0] == segments[2][5] - segments[2][4], "Wrong BSS size")
text_off = struct.unpack_from("<I", nso, 0x10)[0]
modoff = struct.unpack_from("<I", nso, text_off + 4)[0]
check(
    nso[text_off + modoff : text_off + modoff + 4] == b"MOD0",
    "MOD0 is not reachable from the entry header",
)

npdm = (root / "build/finn32.npdm").read_bytes()
check(npdm[:4] == b"META" and not npdm[12] & 1, "NPDM does not select 32-bit code")
cfg = json.loads((root / "build/finn32.json").read_text())
check(
    cfg["is_64_bit"] is False and cfg["address_space_type"] == 0, "Wrong process ABI configuration"
)
exe = (root / "finn32.nsp").read_bytes()
files = pfs(exe)
check(
    files.get("main") == nso and files.get("main.npdm") == npdm,
    "ExeFS does not contain the built code/metadata",
)

nro = (root / "launcher/finn_nx.nro").read_bytes()
check(nro[16:20] == b"NRO0", "Bad launcher NRO header")
core = struct.unpack_from("<I", nro, 24)[0]
check(nro[core : core + 4] == b"ASET", "NRO has no assets section")
ioff, isz, noff, nsz, roff, rsz = struct.unpack_from("<6Q", nro, core + 8)
check(core + roff + rsz == len(nro), "Truncated or trailing NRO RomFS")
check(nsz == 0x4000 and isz > 0, "Missing NACP or icon")
check(
    nro[core + ioff : core + ioff + isz] == (root / "launcher/icon.jpg").read_bytes(),
    "Wrong embedded icon",
)
nacp = nro[core + noff : core + noff + nsz]
check(nacp[:0x200].split(b"\0")[0] == b"Jumping Finn Turbo", "Wrong launcher title")
check(nacp[0x200:0x300].split(b"\0")[0] == b"RadiantDelux", "Wrong displayed launcher author")
check(nacp[0x3060:0x3070].split(b"\0")[0].decode() == VERSION, "NACP version differs from VERSION")
members = romfs(nro[core + roff : core + roff + rsz])
check(members.get("finn32.nsp") == exe, "Embedded payload differs from the compiled ExeFS")
check(
    members.get("finn32.build") == (root / "finn32.build").read_bytes(),
    "Embedded build number differs",
)
check(
    members.get("LICENSES.txt") == license_notices().encode("utf-8"),
    "Third-party notices missing from NRO",
)
forwarder = json.loads((root / "build/forwarder-templates.json").read_text())
check(
    members.get("finn-forwarder-license.txt")
    == (root / "vendor/forwarder/LICENSE.md").read_bytes(),
    "Forwarder license notice missing from NRO",
)
check(
    forwarder["title_id"] == "059669A728222000"
    and forwarder["nro_path"] == "/switch/finn_nx/finn_nx.nro",
    "Unexpected automatic forwarder identity or target",
)
for name, entry in forwarder["templates"].items():
    filename = "finn-auto-" + name + ".nca"
    template = (root / "launcher/romfs" / filename).read_bytes()
    check(members.get(filename) == template, "Embedded forwarder template differs: " + name)
    check(
        len(template) == entry["size"] and sha(template) == entry["sha256"],
        "Forwarder manifest differs: " + name,
    )

report = {
    "status": "packaging_verified_console_test_pending",
    "version": VERSION,
    "author": "RadiantDelux",
    "graphics": "OpenGL ES / Mesa Nouveau (AArch32)",
    "game": "Jumping Finn Turbo Android 1.1.6 / Unity 4.3.0f4",
    "build": (root / "finn32.build").read_text().strip(),
    "checks": [
        "ARM32 ELF and NPDM",
        "all three NSO segments match ELF",
        "NSO SHA-256 hashes and BSS",
        "MOD0 entry header",
        "ExeFS payload",
        "NRO assets, icon and title",
        "embedded RomFS payload and build number",
        "embedded CLR2 controls",
        "all three embedded automatic-forwarder templates and manifest",
    ],
    "automatic_forwarder": forwarder,
    "artifacts": {
        n: {"size": len(b), "sha256": sha(b)}
        for n, b in [("finn32.nsp", exe), ("finn_nx.nro", nro)]
    },
}
(root / "build/verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
