"""Compile the port's managed input helper against the user's exact APK."""

import argparse
import os
import subprocess
import zipfile
from pathlib import Path
from project import ROOT as root, validate_apk

ap = argparse.ArgumentParser()
ap.add_argument("--apk", type=Path, required=True)
ap.add_argument(
    "--compiler",
    type=Path,
    default=Path(os.environ.get("WINDIR", "C:/Windows"))
    / "Microsoft.NET/Framework/v4.0.30319/csc.exe",
)
a = ap.parse_args()
a.apk = validate_apk(a.apk)
refs = root / "build/managed-refs"
refs.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(a.apk) as z:
    for name in ("mscorlib.dll", "UnityEngine.dll", "Assembly-CSharp.dll"):
        p = refs / name
        data = z.read("assets/bin/Data/Managed/" + name)
        if not p.exists() or p.read_bytes() != data:
            p.write_bytes(data)
out = root / "build/FinnControls.dll"
src = root / "managed/FinnControls.cs"
if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
    subprocess.run(
        [
            str(a.compiler),
            "/nologo",
            "/noconfig",
            "/nostdlib+",
            "/target:library",
            "/optimize+",
            "/langversion:3",
            "/out:" + str(out),
            *[
                "/reference:" + str(refs / n)
                for n in ("mscorlib.dll", "UnityEngine.dll", "Assembly-CSharp.dll")
            ],
            str(src),
        ],
        check=True,
    )
b = out.read_bytes()
header = root / "build/finn_controls_assembly.h"
text = "/* Generated from managed/FinnControls.cs; contains only the port helper. */\n"
text += "static const unsigned char finn_controls_assembly[] = {\n"
text += (
    "\n".join(",".join("0x%02x" % v for v in b[i : i + 24]) + "," for i in range(0, len(b), 24))
    + "\n};\n"
)
if not header.exists() or header.read_text() != text:
    header.write_text(text)
print("Managed controls embedded:", len(b), "bytes; CLR 2 metadata")
