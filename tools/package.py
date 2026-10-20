"""Create an APK-free public release, or an explicitly requested personal SD copy."""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from licenses import license_notices
from project import ROOT, VERSION, validate_apk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local-apk", type=Path, help="Include your APK in a personal archive; never publish it"
    )
    args = parser.parse_args()
    apk = validate_apk(args.local_apk) if args.local_apk else None
    report = json.loads((ROOT / "build/verification.json").read_text(encoding="utf-8"))
    nro = ROOT / "launcher/finn_nx.nro"
    digest = hashlib.sha256(nro.read_bytes()).hexdigest()
    if report.get("version") != VERSION or digest != report["artifacts"]["finn_nx.nro"]["sha256"]:
        raise RuntimeError(
            "Rebuild and run verify_build.py for the current version before packaging"
        )

    dist = ROOT / "dist"
    stage = dist / "SD-ready"
    game = stage / "switch/finn_nx"
    game.mkdir(parents=True, exist_ok=True)
    shutil.copy2(nro, game / "finn_nx.nro")
    shutil.copy2(ROOT / "build/verification.json", dist / "verification.json")
    (stage / "LEEME.txt").write_text(
        f"Finn NX {VERSION}\n\n" + (ROOT / "docs/SD_README.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (stage / "LICENSES.txt").write_text(license_notices(), encoding="utf-8")
    files = [stage / "LEEME.txt", stage / "LICENSES.txt", game / "finn_nx.nro"]
    if apk:
        target = game / "JumpingFinnTurbo_android.apk"
        shutil.copy2(apk, target)
        files.append(target)
    suffix = "-local" if apk else ""
    archive = dist / f"Finn-NX-{VERSION}{suffix}-SD.zip"
    # An explicit allowlist keeps unrelated SD-ready files and old APKs out.
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in files:
            output.write(path, path.relative_to(stage).as_posix())
    with zipfile.ZipFile(archive) as output:
        if output.testzip() or output.read("switch/finn_nx/finn_nx.nro") != nro.read_bytes():
            raise RuntimeError("Release archive verification failed")
        if not apk and any(
            name.lower().endswith((".apk", ".ipa", ".so", ".dll")) for name in output.namelist()
        ):
            raise RuntimeError("Game input found in public archive")
    sums = dist / f"SHA256SUMS{suffix}.txt"
    sums.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in (game / "finn_nx.nro", archive)
        ),
        encoding="utf-8",
    )
    print(archive)
    print(sums)
    print(
        "Personal archive includes your APK; do not publish."
        if apk
        else "Public archive verified: no APK or game libraries."
    )


if __name__ == "__main__":
    main()
