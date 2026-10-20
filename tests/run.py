"""Run the local artifact and CPU checks with the user's compatible APK."""

import argparse
import shutil
import subprocess
import sys
import zipfile

from pathlib import Path
from tools.project import ROOT, validate_apk


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
        ("tools.verify_build", []),
        ("tests.check_input_apk", [str(apk)]),
        ("tests.check_cursor", []),
        ("tests.check_audio_open", []),
        ("tests.check_menu_launch", []),
        ("tests.check_forwarder", []),
        ("tests.check_kuser", [str(unity)]),
        ("tests.check_display", [str(unity)]),
        ("tests.check_physx_math", [str(unity)]),
        ("tests.check_audio", [str(unity)]),
        ("tests.check_file_worker", [str(unity)]),
    ]
    for module, arguments in tests:
        subprocess.run([sys.executable, "-m", module, *arguments], cwd=ROOT, check=True)
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
            str(ROOT / "tests/check_controls.ps1"),
        ],
        check=True,
    )
    print("All local checks passed. Real GPU, HOME and input timing still require console testing.")


if __name__ == "__main__":
    main()
