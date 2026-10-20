"""Run the local artifact and CPU checks with the user's compatible APK."""

import argparse
import shutil
import subprocess
import sys
import zipfile

from pathlib import Path
from project import ROOT, validate_apk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    args = parser.parse_args()
    apk = validate_apk(args.apk)
    inputs = ROOT / "build/test-inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    unity = inputs / "libunity.so"
    with zipfile.ZipFile(apk) as archive:
        unity.write_bytes(archive.read("lib/armeabi-v7a/libunity.so"))
    tests = [
        ("verify_build.py", []),
        ("check_input_apk.py", [str(apk)]),
        ("check_cursor.py", []),
        ("check_audio_open.py", []),
        ("check_menu_launch.py", []),
        ("check_forwarder.py", []),
        ("check_kuser.py", [str(unity)]),
        ("check_display.py", [str(unity)]),
        ("check_physx_math.py", [str(unity)]),
        ("check_audio.py", [str(unity)]),
        ("check_file_worker.py", [str(unity)]),
    ]
    for script, arguments in tests:
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / script), *arguments], cwd=ROOT, check=True
        )
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        raise RuntimeError("PowerShell is required for the managed controls check")
    subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "tools/check_controls.ps1"),
        ],
        check=True,
    )
    print("All local checks passed. Real GPU, HOME and input timing still require console testing.")


if __name__ == "__main__":
    main()
