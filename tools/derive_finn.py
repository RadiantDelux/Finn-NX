"""Derive the Mono bridge from the supplied APK, without executing it.

Requires pyelftools and capstone. The shared structural recognizer comes
from aks796/dcr_sea_nx; the native entry signatures are from Finn's own DEX.
"""

import argparse
import json
import struct
from pathlib import Path
from arm32 import Arm32, hexguard
from derive_offsets import derive_mono, derive_gc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("libdir", type=Path)
    ap.add_argument("-o", default=str(Path(__file__).parent.parent / "source/dcr_offsets.h"))
    a = ap.parse_args()
    m = Arm32(str(a.libdir / "libmono.so"))
    info = derive_mono(m)
    derive_gc(m)
    lookup = m.dynsym_def["GC_lookup_thread"]
    base, text = m.text()
    flush = []
    for i in range(0, len(text), 4):
        if struct.unpack_from("<I", text, i)[0] != 0xEF000000:
            continue
        va = base + i
        for k in range(1, 40):
            fn = va - k * 4
            if m.u32(fn) & 0xFFFF0000 != 0xE92D0000:
                continue
            ins = list(m.arm.disasm(m.raw[m.off(fn) : m.off(va) + 4], fn))
            # This older Mono emits MOVW 2 / MOVT 15 rather than MOV 2.
            if any(x.mnemonic == "movw" and x.op_str.endswith("#2") for x in ins) and any(
                x.mnemonic == "movt" and x.op_str.endswith("#0xf") for x in ins
            ):
                flush.append(fn)
            break
    if len(flush) != 1:
        raise RuntimeError("Ambiguous Mono Linux cacheflush function")
    expected = {"last_stop": 16, "stack_ptr": 20, "signal": 12}
    if info["fields"] != expected:
        raise RuntimeError("Unexpected Boehm thread layout")
    defs = {
        "DCR_MONO_RVA_FlushIcache": flush[0],
        "DCR_MONO_RVA_SuspendHandler": info["handler"],
        "DCR_MONO_RVA_LookupThread": lookup,
        "DCR_MONO_GOT_StopCount": info["got"] + info["stop_slot"],
        "DCR_MONO_GOT_AckSem": info["got"] + info["ack_slot"],
        "DCR_MONO_GCT_SIGNAL": 12,
        "DCR_MONO_GCT_LAST_STOP": 16,
        "DCR_MONO_GCT_STACK_PTR": 20,
        "DCR_MONO_GC_SUSPEND_SIG": 30,
        "DCR_MONO_GC_RESTART_SIG": 24,
    }
    lines = [
        "/* Generated from Finn Android 1.1.6 libmono.so; guarded before use. */",
        "#ifndef FINN_MONO_OFFSETS_H",
        "#define FINN_MONO_OFFSETS_H",
        "#include <stdint.h>",
    ]
    for n, v in defs.items():
        lines.append(f"#define {n} 0x{v:x}u")
    for n, key in [
        ("FlushIcache", "DCR_MONO_RVA_FlushIcache"),
        ("SuspendHandler", "DCR_MONO_RVA_SuspendHandler"),
        ("LookupThread", "DCR_MONO_RVA_LookupThread"),
    ]:
        lines.append(
            f"static const uint32_t DCR_MONO_GUARD_{n}[4] = {hexguard(m.guard(defs[key]))};"
        )
    lines.append("#endif")
    Path(a.o).write_text("\n".join(lines) + "\n")
    print(json.dumps(defs, indent=2))


if __name__ == "__main__":
    main()
