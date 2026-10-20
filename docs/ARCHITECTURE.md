# Architecture

Finn NX is a game-specific host for the Android ARMv7 release of Jumping Finn
Turbo. It executes the original native libraries on the Switch CPU and supplies
the Android/JNI services they use.

## Startup and handoff

1. The AArch64 NRO validates the APK and locates an existing Finn forwarder.
2. It checks the override's NPDM identity and ABI, then asks NS whether the title
   is still installed. SD files left behind by a deleted HOME icon are insufficient.
3. If needed, the installer creates its dedicated homebrew title, prepares an
   ARM32 ExeFS override, registers its content with NCM and publishes it with NS.
4. After confirming installation, it requests the HOME application launch.
5. The ARM32 runtime loads the game's libraries, applies guarded compatibility
   patches, binds JNI and enters Unity's render loop.

The forwarder builder uses the published [NCA](https://switchbrew.org/wiki/NCA)
and [CNMT](https://switchbrew.org/wiki/CNMT) formats. SPL encrypts the headers on
the console. No console keys, tickets or commercial game program are bundled.

## Source map

| Directory / file | Responsibility |
| --- | --- |
| `source/finn_boot.c` | Unity 4.3 JNI lifecycle, frame loop and library loading |
| `source/finn_input.c` | Touch injection, controller mapping and pointer rendering |
| `source/finn_controls.c` | Loads and invokes the managed helper on UnityMain |
| `managed/FinnControls.cs` | Original game UI handlers and visible-target selection |
| `source/dcr_audio.c` | FMOD PCM output, resampling and audout buffers |
| `source/mono_rt.c`, `jit_arena.c` | Mono integration and executable memory |
| `source/finn_display.c` | Guarded RGB888/RGBA8888 selection for this Unity build |
| `launcher/source/` | APK validation, installation and HOME handoff |
| `runtime/` | Vendored android32 runtime, with documented local fixes |
| `vendor/` | miniz and the pinned homebrew forwarder loader |

## Compatibility details

- Unity's `nativeResize` receives `width, height, width, height`; its final
  arguments are logical dimensions. The original RGB565 request is redirected
  to Unity's existing RGBA8888 fallback using an instruction guard.
- Linux kuser atomic helpers are redirected before constructors execute.
- Bionic float classification uses Android's ABI codes; PhysX relies on them
  when checking finite poses.
- Finn disables artificial 250 ms condition-variable wakeups because this
  Unity build treats an empty queue after wakeup as a worker shutdown.
- The native host reproduces the Java FMOD start/pause/resume lifecycle.
- The managed helper invokes the original action and restart handlers; it
  does not overwrite cooldowns or saved progress.

Graphics currently use OpenGL ES and Mesa/Nouveau. Vulkan is not implemented.
The AArch32 ABI, memory layout and instruction guards are specific to the exact
APK hash listed in the README.
