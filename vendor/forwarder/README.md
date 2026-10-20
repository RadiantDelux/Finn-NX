# Homebrew forwarder template

`main` and `main.npdm` come from
[`TooTallNate/switch-nsp-forwarder`](https://github.com/TooTallNate/switch-nsp-forwarder/tree/845811585e0b0d8881745afd50eca25d203957fd/romfs/template/exefs),
commit `845811585e0b0d8881745afd50eca25d203957fd` (MIT project).
The embedded loader derives from nx-hbloader; its original ISC notice is
preserved in `LICENSE.md`. These are homebrew loader files, not game binaries.

- `main`: SHA-256 `e135cad353aa4d36d3095a6769e44e5a6f4f82353677b21f8930d1286c741d27`
- `main.npdm`: SHA-256 `62091d193ac96b2f80956f80ed731e9ce57b8ec1f4d207fa9d9522db43feef68`

`tools/build_forwarder.py` verifies both hashes and retargets the NPDM to
Finn's dedicated homebrew title ID. The NCA/RomFS builder and C installer
are local implementations following the published Switchbrew formats.
The installer uses the console's SPL service; no console keys are bundled.
