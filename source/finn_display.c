/* Unity 4.3 requires exact RGB channel sizes when choosing EGL configs.
 * Its default 16-bit branch tries RGB565 only; this mesa32 build offers
 * RGBA8888. Select Unity's existing RGB888 -> RGBA8888 fallback instead.
 * No EGL capabilities are fabricated and no physics code is changed. */
#include <string.h>
#include "finn_display.h"
#include "dcr_patches.h"
#include "util.h"

int finn_display_install(so_module *m) {
    const uint32_t rva = 0x39c240;
    static const uint32_t guard[4] = {0xe5d05081, 0xe3550000, 0x13a05018, 0x03a05010};
    const uint32_t rgb888 = 0x03a05018; /* moveq r5, #24, previously #16 */
    if (m->state != SO_STAGED || !dcr_guard_ok(m, rva, guard, "Unity EGL color request"))
        return 0;
    memcpy((uint8_t *)m->load_base + rva + 12, &rgb888, sizeof rgb888);
    debugPrintf("[display] Unity EGL preference: RGB888/RGBA8888 (guarded APK patch)\n");
    return 1;
}
