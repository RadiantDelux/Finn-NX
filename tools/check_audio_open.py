"""Inject allocation failures into the compiled ARM32 audio initialization."""

import hashlib
import json

from check_input_apk import DATA, Host, ROOT, check, word


def main():
    for failure in range(3):
        host = Host()
        events, freed, allocations = [], [], []
        failing = True

        def service(name):
            events.append(name)
            host.ret()

        for name in ("audoutInitialize", "audoutStartAudioOut", "audoutStopAudioOut", "audoutExit"):
            host.hook(name, lambda name=name: service(name))
        host.hook("audoutGetSampleRate", lambda: host.ret(48000))
        host.hook("audoutGetChannelCount", lambda: host.ret(2))

        def allocate():
            index = len(allocations)
            address = 0 if failing and index == failure else DATA + index * 0x2000
            allocations.append(address)
            host.ret(address)

        def release():
            freed.append(host.reg(0))
            host.ret()

        host.hook("memalign", allocate)
        host.hook("free", release)
        check(host.call("dcr_audio_open") == 0xFFFFFFFF, "Allocation failure was hidden")
        check(freed == allocations[:failure], "Partial audio allocation leaked")
        check(events[-2:] == ["audoutStopAudioOut", "audoutExit"], "Audio service leaked")
        check(not word(host.cpu, host.addr("g_ao_ready")), "Failed output marked ready")
        for index in range(3):
            check(not word(host.cpu, host.addr("g_pcm") + index * 4), "Stale PCM pointer")
        failing = False
        allocations.clear()
        check(host.call("dcr_audio_open") == 0, "Cannot retry after output allocation failure")
        check(word(host.cpu, host.addr("g_ao_ready")) == 1, "Retry did not initialize output")
        before = len(events)
        check(host.call("dcr_audio_open") == 0 and len(events) == before, "Output reopened twice")
    report = {
        "status": "passed",
        "payload_elf_sha256": hashlib.sha256(host.raw).hexdigest(),
        "checks": [
            "each of three allocation failures",
            "buffers freed",
            "audio service closed",
            "retry",
            "idempotent open",
        ],
        "limits": "Compiled ARM32 initialization; allocator and audout modeled.",
    }
    (ROOT / "build/audio-open-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
