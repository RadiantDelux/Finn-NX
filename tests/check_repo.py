"""Check source distribution boundaries, metadata, local links and vendor hashes."""

import hashlib
import re
import subprocess
from pathlib import Path

from tools.build_forwarder import VENDOR_SHA
from tools.licenses import license_notices
from tools.project import APK_SHA256, ROOT, VERSION


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    check(re.fullmatch(r"\d+\.\d+\.\d+", VERSION), "Invalid VERSION")
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    forbidden = {
        ".apk",
        ".ipa",
        ".so",
        ".dll",
        ".nsp",
        ".nro",
        ".elf",
        ".keys",
        ".zip",
        ".7z",
        ".log",
    }
    for name in filter(None, names):
        check(Path(name).suffix.lower() not in forbidden, f"Local artifact tracked: {name}")
        check(
            not name.startswith(("build/", "dist/", "portlibs32/", ".deps/", ".analysis/")),
            f"Generated path tracked: {name}",
        )
    for name, expected in VENDOR_SHA.items():
        check(
            hashlib.sha256((ROOT / "vendor/forwarder" / name).read_bytes()).hexdigest() == expected,
            f"Vendor hash changed: {name}",
        )
    for name in ("README.md", "README.es.md"):
        text = (ROOT / name).read_text(encoding="utf-8-sig")
        check(APK_SHA256 in text and "1.1.6" in text, f"Missing APK requirements: {name}")
        check('src="docs/assets/icon.png"' in text, f"Missing cover: {name}")
    markdown = [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md")]
    for path in markdown:
        text = path.read_text(encoding="utf-8-sig")
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if link.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = link.split("#", 1)[0]
            check(
                (path.parent / target).exists(), f"Broken link in {path.relative_to(ROOT)}: {link}"
            )
    check(
        (ROOT / "docs/assets/icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
        "Cover is not a PNG",
    )
    check("nx-hbloader" in license_notices(), "Missing dependency notices")
    print(f"PASS: source boundaries, metadata, links, cover and vendor hashes ({VERSION})")


if __name__ == "__main__":
    main()
