"""Shared metadata and input validation for build and packaging tools."""

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
APK_SHA256 = re.search(
    r'^#define PORT_APK_SHA256 "([0-9a-f]{64})"$',
    (ROOT / "source/port_config.h").read_text(encoding="utf-8"),
    re.MULTILINE,
).group(1)


def validate_apk(path: Path) -> Path:
    """Accept only the Android 1.1.6 build used by the native hooks."""
    path = path.resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != APK_SHA256:
        raise ValueError(f"Expected Jumping Finn Turbo Android 1.1.6; SHA-256: {APK_SHA256}")
    return path
