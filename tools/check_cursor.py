"""Run the compiled pointer renderer with a modeled GL boundary.

Checks shape, button-matched color and restoration of Unity's GL state.
The generated preview is the actual clear/scissor output, not a GPU capture.
"""

import hashlib
import json
import struct
from PIL import Image
from check_input_apk import Host, ROOT, put, check


def scenario(width, height, enabled=True, visible=True, center=None):
    h = Host()
    u = h.cpu
    pixels = {}
    clears = []
    original = {
        "fb": 17,
        "scissor": enabled,
        "box": (7, 11, 42, 39),
        "color": (0.125, 0.25, 0.5, 0.75),
        "mask": (0, 1, 0, 1),
    }
    state = original.copy()
    cx, cy = center or (width // 2, height // 2)
    u.mem_write(h.addr("x"), struct.pack("<f", cx))
    u.mem_write(h.addr("y"), struct.pack("<f", cy))
    put(u, h.addr("cursor_visible"), int(visible))

    def dimensions():
        put(u, h.reg(0), width)
        put(u, h.reg(1), height)
        h.ret()

    h.hook("dcr_window_size", dimensions)

    def getints():
        values = {0x8CA6: (state["fb"],), 0xC10: state["box"]}[h.reg(0)]
        u.mem_write(h.reg(1), struct.pack("<" + "i" * len(values), *values))
        h.ret()

    h.hook("glGetIntegerv", getints)

    def getcolor():
        check(h.reg(0) == 0xC22, "Unexpected GL float query")
        u.mem_write(h.reg(1), struct.pack("<4f", *state["color"]))
        h.ret()

    h.hook("glGetFloatv", getcolor)

    def getmask():
        check(h.reg(0) == 0xC23, "Unexpected GL mask query")
        u.mem_write(h.reg(1), bytes(state["mask"]))
        h.ret()

    h.hook("glGetBooleanv", getmask)

    def enabled_query():
        check(h.reg(0) == 0xC11, "Unexpected GL enable query")
        h.ret(int(state["scissor"]))

    h.hook("glIsEnabled", enabled_query)

    def enable(value):
        check(h.reg(0) == 0xC11, "Unexpected GL enable")
        state["scissor"] = value
        h.ret()

    h.hook("glEnable", lambda: enable(True))
    h.hook("glDisable", lambda: enable(False))

    def bind():
        check(h.reg(0) == 0x8D40, "Unexpected framebuffer target")
        state["fb"] = h.reg(1)
        h.ret()

    h.hook("glBindFramebuffer", bind)

    def mask():
        state["mask"] = tuple(h.reg(i) for i in range(4))
        h.ret()

    h.hook("glColorMask", mask)

    def scissor():
        state["box"] = tuple(struct.unpack("<i", struct.pack("<I", h.reg(i)))[0] for i in range(4))
        h.ret()

    h.hook("glScissor", scissor)

    def color():
        state["color"] = tuple(
            struct.unpack("<f", struct.pack("<I", h.reg(i)))[0] for i in range(4)
        )
        h.ret()

    h.hook("glClearColor", color)

    def clear():
        check(
            h.reg(0) == 0x4000 and state["fb"] == 0 and state["scissor"],
            "Cursor cleared outside the display/scissor",
        )
        check(state["mask"] == (1, 1, 1, 1), "Color mask was not opened for cursor")
        x, y, w, hh = state["box"]
        rgba = tuple(round(v * 255) for v in state["color"])
        clears.append((x, y, w, hh))
        check(w > 0 and hh > 0, "Invalid clear rectangle")
        for py in range(max(y, 0), min(y + hh, height)):
            for px in range(max(x, 0), min(x + w, width)):
                pixels[px, height - 1 - py] = rgba
        h.ret()

    h.hook("glClear", clear)
    h.call("cursor")
    check(state == original, "Cursor leaked GL state into Unity")
    if not visible:
        check(not pixels and not clears, "Hidden cursor still drew")
        return pixels
    radius = max(6, (height + 36) // 72)
    check(0 < len(clears) <= 64, "Cursor exceeded the small clear budget")
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if not (0 <= x < width and 0 <= y < height):
                continue
            r2 = dx * dx + dy * dy
            expected = (
                (255, 85, 136, 255)
                if r2 <= (radius - 1) ** 2
                else (102, 0, 17, 255)
                if r2 <= radius**2
                else None
            )
            check(pixels.get((x, y)) == expected, "Pointer disk shape/color differs")
    return pixels


def main():
    pixels = scenario(1280, 720)
    scenario(1920, 1080, enabled=False)
    scenario(1280, 720, visible=False)
    for corner in ((0, 0), (1279, 0), (0, 719), (1279, 719)):
        scenario(1280, 720, center=corner)
    preview = Image.new("RGBA", (40, 40), (45, 45, 45, 255))
    for (x, y), color in pixels.items():
        preview.putpixel((x - 640 + 20, y - 360 + 20), color)
    preview.resize((240, 240), Image.Resampling.NEAREST).save(ROOT / "build/cursor-preview.png")
    report = {
        "status": "passed",
        "payload_elf_sha256": hashlib.sha256((ROOT / "finn32.elf").read_bytes()).hexdigest(),
        "fill": "#ff5588",
        "diameter_720p": 21,
        "diameter_1080p": 31,
        "checks": [
            "compiled circular renderer",
            "button atlas pink",
            "720p and 1080p scaling",
            "screen edge clipping",
            "hidden cursor does not draw",
            "Unity GL state restored",
            "no readback or allocation",
        ],
        "limits": "Actual compiled renderer; GL boundary modeled. Visual and timing check on Switch pending.",
    }
    (ROOT / "build/cursor-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
