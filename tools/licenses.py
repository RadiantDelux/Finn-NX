"""Assemble the notices shipped with standalone NROs and release archives."""

from tools.project import ROOT


def license_notices() -> str:
    files = (
        ("Finn NX", "LICENSE"),
        ("android32 runtime", "runtime/LICENSE"),
        ("miniz", "vendor/miniz/LICENSE"),
        ("nx-hbloader forwarder", "vendor/forwarder/LICENSE.md"),
        ("libnx / libnx32", "docs/licenses/libnx.txt"),
        ("Mesa", "docs/licenses/mesa.txt"),
    )
    return (
        "\n\n".join(
            f"{title}\n{'=' * len(title)}\n\n{(ROOT / name).read_text(encoding='utf-8').strip()}"
            for title, name in files
        )
        + "\n"
    )
