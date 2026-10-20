# android32 runtime

This directory contains the subset of [aks796/android32](https://github.com/aks796/android32)
used by Finn NX, based on revision `4b5e470a494c529ae77cd490c88a91bfe28828f3`.
The runtime sources, linker files, import generator and shared launcher are
vendored so a normal clone contains everything required by the port.

Build Finn NX from the project root using [the build guide](../docs/BUILDING.md).
See [architecture](../docs/ARCHITECTURE.md) for how the game uses the runtime and
[THIRD_PARTY.md](../THIRD_PARTY.md) for attribution and local changes.

Generic migration notes, example ports and unused build/export scripts are
omitted. The complete runtime documentation is available in the upstream repository.

The MIT [license](LICENSE) and individual source notices are retained, including
the native loader and libnx-derived code notices.
