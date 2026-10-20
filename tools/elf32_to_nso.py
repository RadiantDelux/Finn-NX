"""Package devkitARM's three load segments as an uncompressed NSO0.

The Windows elf2nso shipped by devkitPro currently accepts only AArch64.
NSO0 itself is architecture-neutral; the NPDM selects AArch32. Layout:
https://switchbrew.org/wiki/NSO
No game binaries are processed by this tool, only the compiled host wrapper.
"""

import hashlib
import struct
import sys
from pathlib import Path


def convert(src, dst):
    data = Path(src).read_bytes()
    h = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    if h[0][:6] != b"\x7fELF\x01\x01" or h[2] != 40 or h[4] != 0:
        raise ValueError("Expected little-endian ARM ELF32 with entry at zero")
    segments = []
    for i in range(h[10]):
        p = struct.unpack_from("<8I", data, h[5] + i * h[9])
        if p[0] == 1:
            segments.append(p)
    if len(segments) != 3 or [p[6] for p in segments] != [5, 4, 6]:
        raise ValueError("Expected RX, R, RW load segments")
    if segments[0][2] != 0 or any(p[2] & 4095 for p in segments):
        raise ValueError("Segments must have page-aligned load addresses")
    out = bytearray(0x1000)
    out[:4] = b"NSO0"
    struct.pack_into("<I", out, 0xC, 0x38)  # uncompressed, all three hashes checked
    name = b"finn32\0"
    out[0x100 : 0x100 + len(name)] = name
    struct.pack_into("<I", out, 0x1C, 0x100)
    struct.pack_into("<I", out, 0x2C, len(name))
    struct.pack_into("<I", out, 0x3C, segments[2][5] - segments[2][4])
    sections = [struct.unpack_from("<10I", data, h[6] + i * h[11]) for i in range(h[12])]
    shstr = sections[h[13]]
    for s in sections:
        start = shstr[4] + s[0]
        name = data[start : data.index(0, start)]
        if name == b".note.gnu.build-id":
            ns, ds, ty = struct.unpack_from("<III", data, s[4])
            pos = s[4] + 12 + ((ns + 3) & ~3)
            out[0x40 : 0x40 + min(ds, 32)] = data[pos : pos + min(ds, 32)]
        if name in [b".dynstr", b".dynsym"]:
            at = 0x90 if name == b".dynstr" else 0x98
            struct.pack_into("<II", out, at, s[3] - segments[1][2], s[5])
    for i, p in enumerate(segments):
        blob = data[p[1] : p[1] + p[4]]
        struct.pack_into("<III", out, 0x10 + i * 0x10, len(out), p[2], len(blob))
        struct.pack_into("<I", out, 0x60 + i * 4, len(blob))
        out[0xA0 + i * 32 : 0xC0 + i * 32] = hashlib.sha256(blob).digest()
        out.extend(blob)
    Path(dst).write_bytes(out)
    print(f"NSO0: {dst}, {len(out)} bytes, ARM32, uncompressed")


if __name__ == "__main__":
    convert(*sys.argv[1:])
