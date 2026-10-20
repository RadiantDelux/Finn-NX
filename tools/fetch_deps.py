"""Fetch the two pinned AArch32 portlibs releases into a local cache.

Hashes are checked before any archive is extracted. No system installation.
"""

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--dest", type=Path, default=root / ".deps")
dest = ap.parse_args().dest.resolve()
dest.mkdir(parents=True, exist_ok=True)
for name, entry in json.loads((root / "dependencies.lock.json").read_text()).items():
    archive = dest / (name + ".zip")
    if not archive.exists():
        urllib.request.urlretrieve(entry["url"], archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != entry["sha256"]:
        raise RuntimeError(f"{name}: downloaded release hash differs from the build lock")
    target = (dest / name).resolve()
    stamp = target / ".archive-sha256"
    if stamp.exists() and stamp.read_text().strip() == entry["sha256"]:
        print(name, "already verified")
        continue
    with zipfile.ZipFile(archive) as z:
        for n in z.namelist():
            if not (target / n).resolve().is_relative_to(target):
                raise RuntimeError("Unsafe archive member")
        z.extractall(target)
    stamp.write_text(entry["sha256"] + "\n")
    print(name, entry["sha256"])
