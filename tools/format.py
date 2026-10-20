"""Format maintained sources, leaving vendored code and generated files intact."""

import argparse
import subprocess
import sys

from tools.project import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sources = []
    for directory in ("source", "launcher/source", "managed", "tests", "tests/managed"):
        sources.extend(
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / directory).glob("*"))
            if path.suffix in (".c", ".h", ".cs")
            and path.name not in ("dcr_offsets.h", "finn_auto_assets.h")
        )
    clang_args = ["--dry-run", "--Werror"] if args.check else ["-i"]
    subprocess.run(["clang-format", *clang_args, *sources], cwd=ROOT, check=True)
    ruff_args = ["--check"] if args.check else []
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", *ruff_args, "tools", "tests"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([sys.executable, "-m", "ruff", "check", "tools", "tests"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
