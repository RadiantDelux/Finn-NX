<p align="center">
  <img src="docs/assets/icon.png" width="192" alt="Jumping Finn Turbo icon">
</p>

<h1 align="center">Finn NX</h1>
<p align="center">Jumping Finn Turbo for Nintendo Switch homebrew</p>
<p align="center">
  <a href="https://github.com/RadiantDelux/Finn-NX/releases">Downloads</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="docs/BUILDING.md">Build from source</a> ·
  <a href="https://github.com/RadiantDelux/Finn-NX/issues">Report an issue</a>
</p>

Finn NX runs the **Android 1.1.6** release of Jumping Finn Turbo on Nintendo
Switch, using the original ARMv7 libraries and Unity/Mono scripts. Graphics
use **OpenGL ES through Mesa/Nouveau**. Touch input and controller input are supported.

The download contains the homebrew launcher and runtime. **Supply your own
compatible APK; the game is not included.** This is an unofficial community port.

## Requirements

- Nintendo Switch running Atmosphère, configured to install and launch homebrew forwarders.
- Access to hbmenu or sphaira and writable space on the SD card.
- The exact Android build below. The iOS IPA is not supported by this port.

| Field | Required value |
| --- | --- |
| Game | Jumping Finn Turbo / Finn Saltarín |
| Android version | **1.1.6** |
| Package | `com.turner.jft` |
| Architecture | `armeabi-v7a` |
| Engine | Unity `4.3.0f4`, Mono |
| APK size | 50,439,654 bytes |

**APK SHA-256**

```text
7b3c4d0058c8f613b0a696fbbdd96b4fd0162e75d3ee85da11d9f38cf768d040
```

Any `.apk` filename is accepted, including an uppercase extension. The launcher
and runtime scan the game directory and validate the whole file by SHA-256.
A different version, repack or modified APK will be rejected.

To check your copy on Windows:

```powershell
Get-FileHash -Algorithm SHA256 "C:\Games\JumpingFinnTurbo.apk"
```

## Installation

1. Download `finn_nx.nro` or the SD archive from [Releases](https://github.com/RadiantDelux/Finn-NX/releases).
2. Put the NRO and your compatible APK in `sd:/switch/finn_nx/`:

   ```text
   switch/
   └── finn_nx/
       ├── finn_nx.nro
       └── your-game.apk
   ```

3. Open `finn_nx.nro` from Album/hbmenu. It reuses an installed Finn forwarder,
   or installs its own HOME icon and requests a launch. No separate NSP download is needed.
4. The first game launch extracts the native libraries from your APK. Let it finish.
   Later launches can use the HOME icon directly.

The NRO is a 64-bit launcher; the game runs as a **32-bit application** after
handoff. Opening it from Album does not run Unity inside the applet.

If automatic setup is unavailable on your configuration, install the NRO with
**Install Forwarder** in sphaira, then open that icon from HOME.

## Controls

| Input | Action |
| --- | --- |
| **Y** | Jake's airborne kick |
| **X** | Recovery / bounce |
| **B** | Initial launch gauge: press once to start, again to kick |
| **B**, during flight | Tap actions for meteorite, rainbow, birds and ice; hold to repeat |
| **L** or **ZL** | Hit a visible penguin on the left |
| **R** or **ZR** | Hit a visible penguin on the right |
| **−** | Restart the current run, like the original restart button; keeps saved progress |
| **+** | Pause / resume through the game's pause menu |
| Left stick | Move and show the pink pointer |
| **A** | Click or drag at the pointer, including menus |
| Right-stick click | Android Back |
| **L + R + +** | Exit |
| Touchscreen | Original touch controls in handheld mode |

Kick and recovery respect the original availability and cooldowns. Other buttons
hide the pointer; **A** keeps it visible while clicking. Moving the stick shows it again.
A restart reloads the current scene and may briefly display its normal loading transition.

## Updating and saves

Replace `sd:/switch/finn_nx/finn_nx.nro` and open Finn again. The runtime updates
the ARM32 program for the existing HOME icon. Keep your APK and the `data/` directory;
saved progress lives under `sd:/switch/finn_nx/data/`.

The displayed NRO and generated forwarder author is **RadiantDelux**. HOME icon,
title and author metadata are copied when the forwarder is installed; reinstall
an existing forwarder to refresh those fields after an update.

The automatic forwarder uses homebrew title ID `059669A728222000`. Its generated
program override is `sd:/atmosphere/contents/059669A728222000/exefs.nsp`.
`title_id.txt` records the forwarder IDs associated with this installation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| APK missing or rejected | Directory, Android version and the exact SHA-256 above |
| Forwarder installation or handoff fails | `sd:/switch/finn_nx/forwarder-install.log`; try the HOME icon or sphaira fallback |
| Black screen or crash | `sd:/switch/finn_nx/debug.log` and `crash.log`, if generated |
| A controller action does nothing | Check that the corresponding original action is currently available |

Include the port version, launch mode, Atmosphère version and relevant logs in a
[bug report](https://github.com/RadiantDelux/Finn-NX/issues/new?template=bug_report.yml).
Do not attach your APK or saves. See [testing notes](docs/TESTING.md) for what local checks cover.

## Development and credits

- [Build instructions](docs/BUILDING.md), [architecture](docs/ARCHITECTURE.md), [changelog](CHANGELOG.md).
- [Publication review and resolved findings](docs/REVIEW.md).
- Based on [aks796/android32](https://github.com/aks796/android32) and the Unity/Mono
  integration from [aks796/dcr_sea_nx](https://github.com/aks796/dcr_sea_nx).
- AArch32 support builds on xerpi/vita2hos, libnx32 and Mesa. The forwarder uses nx-hbloader.
- Full attribution, versions and licenses: [THIRD_PARTY.md](THIRD_PARTY.md).

Port and runtime code are distributed under the [MIT license](LICENSE), with
third-party notices retained. The icon, game assets, names and trademarks remain
the property of their respective owners.
