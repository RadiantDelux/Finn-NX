<p align="center">
  <img src="docs/assets/icon.png" width="176" alt="Jumping Finn Turbo">
</p>

<h1 align="center">Finn NX</h1>
<p align="center">Jumping Finn Turbo / Finn Saltarín for Nintendo Switch</p>
<p align="center">
  <a href="https://github.com/RadiantDelux/Finn-NX/releases/latest"><b>Download</b></a> ·
  <a href="README.es.md">Español</a> ·
  <a href="#controls">Controls</a> ·
  <a href="https://github.com/RadiantDelux/Finn-NX/issues">Report an issue</a>
</p>

An unofficial native port of **Jumping Finn Turbo**, based on the **Android 1.1.6**
release. Port by [RadiantDelux](https://github.com/RadiantDelux).

## Features

- Original ARMv7 game code runs on the Switch CPU through the android32 runtime.
- OpenGL ES graphics through Mesa/Nouveau.
- Touch controls in handheld mode and controller support for docked play.
- Automatic HOME forwarder setup from the NRO, including launch from Album/hbmenu.

**The game is not included. You must supply your own compatible APK.**

## Requirements

- Nintendo Switch running Atmosphère, configured to install and launch homebrew forwarders.
- hbmenu or sphaira, plus writable space on the SD card.
- **Jumping Finn Turbo for Android, version 1.1.6**, with these exact details:

| APK | Required value |
| --- | --- |
| Package | `com.turner.jft` |
| Architecture | `armeabi-v7a` (32-bit ARM) |
| File size | 50,439,654 bytes |
| SHA-256 | See below |

```text
7b3c4d0058c8f613b0a696fbbdd96b4fd0162e75d3ee85da11d9f38cf768d040
```

The filename can be anything ending in `.apk`, including uppercase. Finn NX scans
its folder and checks the full SHA-256. Other versions and modified APKs are rejected.

<details>
<summary>Check your APK on Windows</summary>

```powershell
Get-FileHash -Algorithm SHA256 "C:\Games\JumpingFinnTurbo.apk"
```

</details>

## Installation

1. Download **Finn-NX-0.1.11-SD.zip** from [the latest release](https://github.com/RadiantDelux/Finn-NX/releases/latest) and extract it to the SD root.
2. Add your compatible APK to the same folder as the NRO:

   ```text
   sd:/switch/finn_nx/
   ├── finn_nx.nro
   └── your-game.apk
   ```

3. Open **Finn NX** from Album/hbmenu. The NRO installs or reuses its HOME forwarder and starts the game.
4. Let the first launch finish extracting the native libraries. Afterwards, launch from the HOME icon.

You can also download the standalone `finn_nx.nro` and create the folder yourself.
A separate NSP is not needed. The game runs as a full **32-bit application** after
handoff; Unity does not run inside the Album applet.

If automatic installation fails, use **Install Forwarder** in sphaira on the NRO,
then open its HOME icon.

## Controls

| Input | Action |
| --- | --- |
| Touchscreen | Original touch controls |
| **Y** | Jake's airborne kick |
| **X** | Recovery / bounce |
| **B** | Initial kick: press once to start the gauge, again to kick |
| **B** during flight | Tap actions for meteorite, rainbow, birds and ice; hold to repeat |
| **L / ZL** | Hit a visible penguin on the left |
| **R / ZR** | Hit a visible penguin on the right |
| **−** | Restart the current run, keeping saved progress |
| **+** | Pause menu |
| Left stick | Move and show the pink pointer |
| **A** | Click / drag with the pointer, including menus |
| Right-stick click | Back |
| **L + R + Plus** | Exit |

Actions respect the game's availability and cooldowns. Other buttons hide the
pointer; **A** keeps it visible. Move the stick to show it again.

## Updating and support

Replace `sd:/switch/finn_nx/finn_nx.nro` and open Finn again. **Keep your APK and
`data/` folder**; saves are stored in `sd:/switch/finn_nx/data/`.

The NRO and generated forwarder display **RadiantDelux** as author. To refresh
an older HOME icon's author or artwork, remove that forwarder through software
management and open the updated NRO to reinstall it.

For setup failures, check `forwarder-install.log` in the game folder. For a black
screen or crash, check `debug.log` and `crash.log`, if generated. Include the port
version, Atmosphère version, launch method and relevant logs in a
[bug report](https://github.com/RadiantDelux/Finn-NX/issues/new?template=bug_report.yml).

## Building from source

The supported build host is Windows with PowerShell, devkitPro and native Python 3.10+:

```powershell
git clone https://github.com/RadiantDelux/Finn-NX.git
cd Finn-NX
./build.ps1 -ApkPath "C:\Games\JumpingFinnTurbo.apk"
```

See [the build guide](docs/BUILDING.md) for the toolchain and packaging steps.
Build tools live in `tools/`; regression checks live in `tests/`.
[Architecture](docs/ARCHITECTURE.md) · [Testing](docs/TESTING.md) · [Contributing](CONTRIBUTING.md)

## Credits and license

- **RadiantDelux** — Finn NX port, controls and HOME forwarder integration.
- **aks796** — [android32](https://github.com/aks796/android32), [dcr_sea_nx](https://github.com/aks796/dcr_sea_nx), libnx32 and mesa32.
- **xerpi**, **TheOfficialFloW**, **fgsfds** and **Switchbrew** — AArch32, native loader and libnx work.
- **Mesa/Nouveau contributors** — graphics support; **nx-hbloader contributors** — forwarder loader.
- **Cartoon Network / Turner and the original creators** — game and artwork.

Source code is distributed under the [MIT license](LICENSE), with dependency
notices retained in [THIRD_PARTY.md](THIRD_PARTY.md) and the release packages.
Game assets, names and trademarks belong to their respective owners. Finn NX is
an unofficial community project.
