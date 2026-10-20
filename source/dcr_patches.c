/* Patch only the instructions independently recovered from Finn's APK.
 * Never reuse another game's Unity/Mono offsets. */
#include <string.h>
#include "dcr_patches.h"
#include "util.h"

int dcr_guard_ok(so_module *m, uint32_t rva, const uint32_t guard[4], const char *name) {
    if (rva > m->load_size || m->load_size - rva < 16)
        return 0;
    const void *base = m->state == SO_STAGED ? m->load_base : m->load_virtbase;
    const void *p = (const void *)((uintptr_t)base + rva);
    if (!memcmp(p, guard, 16))
        return 1;
    debugPrintf("[finn] %s guard mismatch at +%08lx; library version rejected\n", name,
                (unsigned long)rva);
    return 0;
}

int dcr_hook(so_module *m, uint32_t rva, const uint32_t guard[4], void *dest, const char *name) {
    if (!dcr_guard_ok(m, rva, guard, name))
        return 0;
    hook_arm((uintptr_t)m->load_virtbase + rva, (uintptr_t)dest);
    return 1;
}
