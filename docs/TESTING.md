# Testing

Gameplay and audio have been reported working on the user's Switch. Local
automation validates built code and file formats; it does not substitute for
testing real graphics, audio timing, input latency or HOME behavior.

## Local checks

After a full build, run:

```powershell
python tools/check.py --apk "C:\Games\JumpingFinnTurbo.apk"
```

| Check | What it covers |
| --- | --- |
| `verify_build.py` | ELF32/NSO segments, hashes, NPDM, NRO assets, version, embedded payload and notices |
| `check_input_apk.py` | Actual ARM32 input routing, X/Y mapping, restart edges, touch cancellation, cursor visibility and APK hashing |
| `check_cursor.py` | Actual pointer renderer with modeled GL; circle, color, scaling, clipping and state restoration |
| `check_audio_open.py` | Allocation-failure cleanup and retry in the compiled audio initializer |
| `check_audio.py` | JNI lifecycle, PCM conversion, pause/resume and thread failure cleanup |
| `check_menu_launch.py` | Actual ARM64 routing; missing/deleted forwarders, identity, NS checks and launch failures |
| `check_forwarder.py` | Actual ARM64 installer with modeled services; NCA/IVFC/PFS, AES-XTS, CNMT, registration, collisions and partial failures |
| `check_kuser.py` | Original Unity atomics with the compiled Linux-helper redirects |
| `check_display.py` | Resize arithmetic and original EGL config selection |
| `check_physx_math.py` | Bionic classification and original PhysX finite-pose checks |
| `check_file_worker.py` | Original Unity APK reader with the compiled condition-variable shims |
| `check_controls.ps1` | Compiled managed helper against modeled Unity/game boundaries; 26 scenarios |

Reports and the modeled pointer preview are written under `build/`. The tools
extract only local test inputs from the validated APK. Filesystem, JNI, GPU and
Switch services are modeled as documented by each report. AES tests use an
artificial key; they do not read console keys.

The audio, PhysX and file-worker tools optionally accept `--baseline <old.elf>`
to reproduce earlier defects. Historical ELFs are not needed for current-code
checks and are not distributed in the source repository.

## Checks without the game

```text
python tools/check_repo.py
python tools/format.py --check
cc -std=c11 -Wall -Wextra -Werror -Iruntime/source tools/tests/exefs_checks.c -o build/exefs_checks
```

Run the resulting parser test executable. On Windows,
`./tools/check_controls.ps1 -CompileHelper` compiles the helper against modeled
boundaries without an APK. A normal local run uses the helper built against the
real APK's references instead.

GitHub Actions runs source hygiene, formatting, malformed ExeFS/NPDM checks and
the modeled managed controls. It does not compile or distribute the commercial
game and does not claim a full Switch build.

## Console verification

Before promoting a release, check cold launch from HOME and Album, deletion and
reinstallation of the forwarder, handheld/docked input, audio after suspend and
resume, a run restart, and updating while retaining saves. Record the port
version, launch mode and Atmosphère version with any failure logs.
