"""Build plaintext homebrew NCA templates, encrypted by SPL on the console.

No console keys, tickets or commercial content are included. Layouts follow
https://switchbrew.org/wiki/NCA and /wiki/CNMT. Standard library only.
"""

import hashlib
import json
import struct
from pathlib import Path
from licenses import license_notices

ROOT = Path(__file__).resolve().parent.parent
NRO_PATH = "/switch/finn_nx/finn_nx.nro"
TITLE_ID = 0x0500000000000000 | (
    int.from_bytes(
        hashlib.sha256(("finn_nx:auto-forwarder:" + NRO_PATH + ":v1").encode()).digest()[:8],
        "little",
    )
    & 0x00FFFFFFFFFFF000
)
BLOCK = 0x4000
VENDOR_SHA = {
    "main": "e135cad353aa4d36d3095a6769e44e5a6f4f82353677b21f8930d1286c741d27",
    "main.npdm": "62091d193ac96b2f80956f80ed731e9ce57b8ec1f4d207fa9d9522db43feef68",
}


def sha(b):
    return hashlib.sha256(b).digest()


def align(n, a):
    return (n + a - 1) // a * a


def pad(b, a):
    return b + bytes(align(len(b), a) - len(b))


def put(b, p, fmt, *v):
    struct.pack_into("<" + fmt, b, p, *v)


def pfs(files):
    names = b""
    entries = b""
    data = b""
    for name, b in files.items():
        entries += struct.pack("<QQII", len(data), len(b), len(names), 0)
        names += name.encode() + b"\0"
        data += b
    names += bytes(align(16 + len(entries) + len(names), 32) - (16 + len(entries) + len(names)))
    return b"PFS0" + struct.pack("<III", len(files), len(names), 0) + entries + names + data


def path_hash(name):
    h = 123456789
    for c in name.encode():
        h = ((h >> 5) | (h << 27) & 0xFFFFFFFF) ^ c
    return h % 3


def romfs(files):
    dh = [0xFFFFFFFF] * 3
    dh[path_hash("")] = 0
    dirs = struct.pack("<6I", 0, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0xFFFFFFFF, 0)
    fh = [0xFFFFFFFF] * 3
    table = bytearray()
    body = bytearray()
    names = list(files)
    offsets = []
    for name in names:
        offsets.append(len(table))
        table += bytes(32 + align(len(name.encode()), 4))
    for i, name in enumerate(names):
        b = files[name]
        body += bytes(align(len(body), 16) - len(body))
        at = offsets[i]
        bucket = path_hash(name)
        put(
            table,
            at,
            "IIQQII",
            0,
            offsets[i + 1] if i + 1 < len(names) else 0xFFFFFFFF,
            len(body),
            len(b),
            fh[bucket],
            len(name.encode()),
        )
        table[at + 32 : at + 32 + len(name.encode())] = name.encode()
        fh[bucket] = at
        body += b
    dh_off = 0x50
    dir_off = dh_off + 12
    fh_off = dir_off + len(dirs)
    ft_off = fh_off + 12
    data_off = align(ft_off + len(table), 0x200)
    head = struct.pack(
        "<10Q", 0x50, dh_off, 12, dir_off, len(dirs), fh_off, 12, ft_off, len(table), data_off
    )
    return (
        pad(head + struct.pack("<3I", *dh) + dirs + struct.pack("<3I", *fh) + table, 0x200) + body
    )


def pfs_section(files, block=0x10000):
    data = pfs(files)
    hashes = b"".join(sha(data[i : i + block]) for i in range(0, len(data), block))
    fs = bytearray(0x200)
    put(fs, 0, "HBBB", 2, 1, 2, 1)
    fs[8:40] = sha(hashes)
    put(fs, 0x28, "IIQQQQ", block, 2, 0, len(hashes), align(len(hashes), 0x200), len(data))
    return fs, pad(pad(hashes, 0x200) + data, 0x200)


def romfs_section(files):
    leaf = romfs(files)
    levels = [None] * 6
    levels[5] = pad(leaf, BLOCK)
    for i in range(4, -1, -1):
        src = levels[i + 1]
        levels[i] = pad(b"".join(sha(src[x : x + BLOCK]) for x in range(0, len(src), BLOCK)), BLOCK)
    fs = bytearray(0x200)
    put(fs, 0, "HBBB", 2, 0, 3, 1)
    put(fs, 8, "4sIII", b"IVFC", 0x20000, 32, 7)
    off = 0
    for i, level in enumerate(levels):
        put(fs, 0x18 + i * 24, "QQII", off, len(leaf) if i == 5 else len(level), 14, 0)
        off += len(level)
    fs[0xC8:0xE8] = sha(levels[0])
    return fs, b"".join(levels)


def nca(kind, sections):
    h = bytearray(0xC00)
    h[0x200:0x204] = b"NCA3"
    h[0x205] = kind
    put(h, 0x210, "Q", TITLE_ID)
    put(h, 0x21C, "I", 0x000C1100)
    body = b""
    for i, (fs, b) in enumerate(sections):
        start = 0xC00 + len(body)
        put(h, 0x240 + i * 16, "III", start // 512, (start + len(b)) // 512, 1)
        h[0x400 + i * 512 : 0x600 + i * 512] = fs
        h[0x280 + i * 32 : 0x2A0 + i * 32] = sha(fs)
        body += b
    put(h, 0x208, "Q", len(h) + len(body))
    return bytes(h) + body


def build():
    vendor = ROOT / "vendor/forwarder"
    assets = {name: (vendor / name).read_bytes() for name in VENDOR_SHA}
    for name, b in assets.items():
        if sha(b).hex() != VENDOR_SHA[name]:
            raise RuntimeError("Forwarder template changed: " + name)
    npdm = bytearray(assets["main.npdm"])
    assert npdm[:4] == b"META" and npdm[12] & 1
    aci, acid = struct.unpack_from("<I", npdm, 0x70)[0], struct.unpack_from("<I", npdm, 0x78)[0]
    for at in (aci + 0x10, acid + 0x210, acid + 0x218):
        put(npdm, at, "Q", TITLE_ID)
    forwarder = romfs_section({"nextNroPath": NRO_PATH.encode(), "nextArgv": NRO_PATH.encode()})
    program = nca(0, [pfs_section({"main": assets["main"], "main.npdm": npdm}), forwarder])
    nacp = bytearray((ROOT / "launcher/finn_nx.nacp").read_bytes())
    nacp[0x3025] = 0
    nacp[0x3026] = 0
    nacp[0x3027] = 1
    nacp[0x3034] = 0
    nacp[0x3035] = 0
    nacp[0x3036] = 0
    nacp[0x30F0] = 2
    nacp[0x3213] = 0
    for at in (0x3038, 0x3078, 0x30F8):
        put(nacp, at, "Q", TITLE_ID)
    put(nacp, 0x3070, "Q", TITLE_ID ^ 0x1000)
    for at in range(0x30B0, 0x30F0, 8):
        put(nacp, at, "Q", TITLE_ID)
    # This homebrew saves to SD, never to a system save archive.
    for at in (0x3080, 0x3088, 0x3090, 0x3098, 0x3148, 0x3150, 0x3158, 0x3160):
        put(nacp, at, "Q", 0)
    control = nca(
        2,
        [
            romfs_section(
                {
                    "control.nacp": nacp,
                    "icon_AmericanEnglish.dat": (ROOT / "launcher/icon.jpg").read_bytes(),
                }
            )
        ],
    )
    cnmt = bytearray(32 + 16 + 2 * 56 + 32)
    put(cnmt, 0, "QIBBHHHBBBBI", TITLE_ID, 0, 0x80, 0, 16, 2, 0, 0, 5, 0, 0, 0)
    put(cnmt, 32, "QII", TITLE_ID | 0x800, 0, 0)
    name = "Application_%016X.cnmt" % TITLE_ID
    meta = nca(1, [pfs_section({name: cnmt}, 0x1000)])
    out = ROOT / "launcher/romfs"
    out.mkdir(parents=True, exist_ok=True)
    notice = out / "finn-forwarder-license.txt"
    license_bytes = (vendor / "LICENSE.md").read_bytes()
    if not notice.exists() or notice.read_bytes() != license_bytes:
        notice.write_bytes(license_bytes)
    notices = out / "LICENSES.txt"
    notices_bytes = license_notices().encode("utf-8")
    if not notices.exists() or notices.read_bytes() != notices_bytes:
        notices.write_bytes(notices_bytes)
    manifest = {"title_id": "%016X" % TITLE_ID, "nro_path": NRO_PATH, "templates": {}}
    for name, b in [("program", program), ("control", control), ("meta", meta)]:
        p = out / ("finn-auto-" + name + ".nca")
        if not p.exists() or p.read_bytes() != b:
            p.write_bytes(b)
        manifest["templates"][name] = {"size": len(b), "sha256": sha(b).hex()}
    (ROOT / "build/forwarder-templates.json").write_text(json.dumps(manifest, indent=2) + "\n")
    header = "/* Generated by tools/build_forwarder.py. No console keys. */\n"
    header += "#define FINN_AUTO_TITLE_ID 0x%016XULL\n" % TITLE_ID
    for name, entry in manifest["templates"].items():
        header += "static const unsigned char finn_auto_%s_sha[32]={%s};\n" % (
            name,
            ",".join("0x" + entry["sha256"][i : i + 2] for i in range(0, 64, 2)),
        )
    p = ROOT / "launcher/source/finn_auto_assets.h"
    if not p.exists() or p.read_text() != header:
        p.write_text(header)
    print(
        "Forwarder templates:",
        manifest["title_id"],
        sum(x["size"] for x in manifest["templates"].values()),
        "bytes (headers encrypted at install time)",
    )
    return manifest


if __name__ == "__main__":
    build()
