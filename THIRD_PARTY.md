# Third-party code and notices

Finn NX retains the original authors' notices. The `dcr_` prefix in shared
Unity/Mono adapters is kept for compatibility with the inherited runtime API;
it does not identify an additional game dependency.

| Component | Revision / release | License / location |
| --- | --- | --- |
| [aks796/android32](https://github.com/aks796/android32) | `4b5e470a494c529ae77cd490c88a91bfe28828f3` | MIT; `runtime/`, original `runtime/LICENSE` retained |
| [aks796/dcr_sea_nx](https://github.com/aks796/dcr_sea_nx) | `1fe4f3a9da70c00699b6ddb5f0984d5cef78e084` | MIT; Unity/Mono, JIT, JNI, audio and preferences adapters in `source/` |
| [aks796/libnx32](https://github.com/aks796/libnx32) | Release `4.12.0`, archive hash in `dependencies.lock.json` | ISC; [notice](docs/licenses/libnx.txt) |
| [aks796/mesa32](https://github.com/aks796/mesa32) | Pinned archive SHA-256 in `dependencies.lock.json` | Mesa and component licenses; [notice](docs/licenses/mesa.txt) |
| [miniz](https://github.com/richgel999/miniz) | `2948eebafc5b9f1c69bebed80333e403a09bd62d` | MIT; `vendor/miniz/LICENSE` |
| [TooTallNate/switch-nsp-forwarder](https://github.com/TooTallNate/switch-nsp-forwarder) | `845811585e0b0d8881745afd50eca25d203957fd` | MIT project; nx-hbloader binary with original ISC notice in `vendor/forwarder/LICENSE.md` |

The AArch32 toolchain and libnx32 build on xerpi/vita2hos. The native library
loader credits Andy Nguyen and fgsfds in its source. Graphics work depends on
the Mesa/Nouveau Switch contributors, including the work underlying DanTico's
Switch Mesa ecosystem. Finn NX currently uses OpenGL ES, not Vulkan.

## Local adaptations

- Unity 4.3 activity/lifecycle, API compatibility, FMOD initialization and offsets
  are adapted for Finn's exact Android 1.1.6 build. Crossy Road offsets are not used.
- `runtime/` retains the port's atomic helper activation, condition-variable
  configuration, diagnostic changes and Windows ELF32-to-NSO packaging support.
- `runtime/source/dcr_exefs.h` now uses overflow-safe ExeFS/NPDM bounds checks.
- Only the runtime sources, build inputs and shared launcher used by Finn NX are
  vendored. Generic port examples, migration notes and unused build/export
  scripts are omitted; the full documentation remains available upstream.
- Mono offsets and instruction guards for the supported APK are checked in as
  `source/dcr_offsets.h`; the retired analysis scripts are not part of the build.
- Maintained port sources and Python tools use the repository's formatting rules;
  the vendored runtime and miniz retain their upstream style.
- The NCA/RomFS builder and installer are local implementations of published
  Switchbrew formats. No sphaira implementation code is included.
- `vendor/forwarder/README.md` records the loader's hashes and provenance.

`tools.licenses` bundles notices inside the NRO and in public release archives.
The game libraries, managed game assemblies and resources are read from each
user's APK. They are not included in the source tree or public release archives.
The supplied cover icon is game artwork and is not covered by the MIT code license.
