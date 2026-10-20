# Source review — 0.1.10

The publication review covered the game host, managed controls, forwarder
handoff/installer, build scripts, distribution boundaries and documentation.
Vendored runtime code retains upstream attribution and style.

## Resolved findings

| Finding | Resolution | Validation |
| --- | --- | --- |
| ExeFS offset/size addition could wrap before its bounds check | Compare against the remaining buffer length | Native parser regression |
| NPDM offset addition could wrap in a 32-bit process | Check offsets and remaining lengths before accessing headers | Native parser regression |
| Audio allocation failure left buffers and audout open | Free partial allocations, close output and permit retry | ARM32 fault injection |
| Build depended on a workstation-specific Python path | Explicit APK, Python, SDK and cache parameters | Windows build and artifact checks |
| Personal packaging included the APK by default | APK-free public package; explicit personal archive option | Archive contents and checksums |
| Version strings and action bits were scattered | Single `VERSION` file and named controller actions | NACP version and ARM32 routing checks |
| Main README mixed installation with historical analysis | English/Spanish guides and separate technical notes | Local link and metadata audit |

The parser test covers valid input, overflowing file offsets and sizes, invalid
string offsets and overflowing NPDM offsets. ARM32 allocation-failure tests
cover each output buffer, cleanup, retry and repeated initialization.

The controller mapping and original managed handlers are preserved. Formatting
changes are isolated from the two functional error-path fixes. Public artifacts
are checked against their build inputs and bundled notices.

## Limits

Local CPU and managed checks model the operating system and game boundaries.
Real GPU presentation, audio latency and HOME installation/handoff remain
console checks. Historical ELF comparisons are optional and stay local.
The inherited runtime still emits some diagnostic-format warnings with the
pinned AArch32 SDK's `long` typedefs; the build does not suppress them.

The source tree excludes the APK, game libraries, extracted managed assemblies,
build outputs, saves and logs. The two pinned files in `vendor/forwarder/` are
homebrew loader assets, with their hashes and license recorded.
