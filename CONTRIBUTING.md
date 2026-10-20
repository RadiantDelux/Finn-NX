# Contributing

Keep changes focused and explain their effect on the supported Android build.
Read [BUILDING.md](docs/BUILDING.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[TESTING.md](docs/TESTING.md) before changing native hooks or the Mono bridge.

## Development

- Use `python -m tools.format` for maintained C, headers, C# and Python tools.
- Keep upstream notices intact. Avoid unrelated formatting of `runtime/` and
  `vendor/`; document substantive runtime changes in `THIRD_PARTY.md`.
- Name controller actions by behavior rather than by their physical button.
- Preserve instruction guards and the exact APK validation when changing hooks.
- Include a focused regression check for parsing, lifecycle or state changes.
  State explicitly which boundaries are modeled and what was checked on hardware.
- Use `VERSION` when preparing a release. Rebuild and run the relevant checks.

APKs, IPAs, game libraries, managed game assemblies, extracted assets, console
keys, saves and local logs must not be committed or uploaded as release assets.
The supplied project icon is retained for identification; it is not covered by
the source-code license.

## Pull requests and reports

Describe the concrete problem, resulting behavior and validation. Include the
port and Atmosphère versions for console failures. Attach only relevant logs,
after removing any personal details; do not attach the APK or saved games.

Public release archives are produced by `python -m tools.package` without
`--local-apk`. Verify their SHA-256 and contents before publishing.
