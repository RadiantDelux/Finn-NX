# Building Finn NX

The supported build host is **Windows with PowerShell**. A full build needs the
user's verified APK; it cannot be reproduced by CI without that local input.

## Toolchain

- devkitPro, including devkitARM, devkitA64, switch-tools, libnx and MSYS2.
- Native Windows Python 3.10 or newer. MSYS2 Python is used only inside the shell build.
- The .NET Framework C# compiler at
  `%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe`.
- The compatible [Android 1.1.6 APK](../README.md#requirements).

Use a checkout path without spaces; the inherited Makefiles use unquoted include paths.

```powershell
git clone https://github.com/RadiantDelux/Finn-NX.git
cd Finn-NX
./build.ps1 -ApkPath "C:\Games\JumpingFinnTurbo.apk"
```

If Python or devkitPro is installed elsewhere:

```powershell
./build.ps1 -ApkPath "C:\Games\JumpingFinnTurbo.apk" `
  -PythonExe "C:\Python312\python.exe" -DevkitPro "C:\devkitPro"
```

`-DepsDir` overrides the default `.deps/` cache. The script downloads the pinned
libnx32 and mesa32 archives from `dependencies.lock.json` and checks their SHA-256
before extraction. It does not install them globally.

## Outputs

| Path | Purpose |
| --- | --- |
| `launcher/finn_nx.nro` | Deployable launcher with the ARM32 runtime embedded |
| `finn32.elf` | ARM32 debug symbols, used by the CPU checks |
| `finn32.nsp` | Internal ExeFS payload, not an installable game NSP |
| `build/verification.json` | Artifact hashes and structural checks |
| `build/compile.log`, `build/launcher.log` | Compiler diagnostics |

The helper in `managed/FinnControls.cs` is compiled against DLLs extracted from
the APK. Only the port's own helper is embedded; the game's DLLs stay local.
`VERSION` supplies the payload banner, process metadata and NRO display version.

## Validation

Run Python modules from the project root. Install the developer dependencies
into the same native Python environment:

```powershell
python -m pip install -r requirements-dev.txt
python -m tools.format --check
python -m tests.run --apk "C:\Games\JumpingFinnTurbo.apk"
```

The checks read the built ELFs and run ARM code with modeled system boundaries.
See [TESTING.md](TESTING.md) for coverage and hardware limitations.

## Packaging

```powershell
python -m tools.package
```

This creates `dist/Finn-NX-<version>-SD.zip`, `dist/SD-ready/` and
`dist/SHA256SUMS.txt`. Public archives contain the NRO, instructions and license
notices. They never include an APK by default.

For a personal SD copy only, `python -m tools.package --local-apk "C:\Games\JumpingFinnTurbo.apk"`
creates a separately named `-local-SD.zip`. Do not upload that archive.

Dependency and compiler versions affect code generation. The timestamped build
identifier also changes output hashes; byte-identical builds are not promised.

## Build tools

The Python files in `tools/` are used by the supported build or development
workflow. None need to be copied to the SD card.

| Module | Purpose |
| --- | --- |
| `tools.build_controls` | Compile the port's C# helper against the verified APK |
| `tools.fetch_deps` | Download and verify the pinned libnx32 and mesa32 archives |
| `tools.elf32_to_nso` | Package the ARM32 ELF; Windows devkitPro's converter accepts only AArch64 |
| `tools.build_forwarder` | Generate the NRO's HOME forwarder templates and license notices |
| `tools.verify_build` | Check the compiled payload, NRO, metadata and embedded files |
| `tools.package` | Create the public SD archive and checksums |
| `tools.format` | Format or check the maintained sources |
| `tools.project`, `tools.licenses` | Shared metadata, APK validation and license text |

`runtime/tools/gen_imports.py` checks `source/imports.c` against the cached symbol
list in `tools/imports_needed.txt` and the rules in `tools/imports.cfg`. These
are build inputs, not game binaries. The regression suite lives in `tests/`.
