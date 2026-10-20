# Changelog

## 0.1.11

- Set the displayed NRO and generated HOME forwarder author to RadiantDelux.
- Rebuild NACP metadata when launcher settings change; retain dependency notices.

## 0.1.10

- Initial public source release, with English and Spanish installation and control guides.
- Configurable Windows build with an explicit APK path, pinned dependencies and a single version file.
- Public packaging excludes the game; standalone NROs carry third-party license notices.
- Uniform formatting, named action flags and shared function declarations.
- Reject overflowing ExeFS/NPDM offsets and release partially allocated audio buffers on failure.
- Add parser, allocation-failure and repository checks, plus CI for checks that do not need the APK.

## 0.1.9

- Check the system's installed state before reusing a forwarder whose files remain on SD.
- Confirm newly installed forwarders before requesting a launch.
- Map Y to Jake's kick and X to recovery.

## 0.1.8

- Map − to the original run-restart handler instead of a synchronous screenshot.
- Enlarge the pointer, make it circular and use the game's pink button color.
- Hide the pointer with action buttons; preserve it for A clicks.

## 0.1.6–0.1.7

- Validate APKs by full SHA-256 under any `.apk` filename.
- Add controller actions for docked play and automatic HOME forwarder installation/handoff.

## 0.1.1–0.1.5

- Bring up Unity/Mono, correct Android atomic helpers, worker synchronization,
  resize/EGL selection, PhysX float classification and the FMOD audio lifecycle.
