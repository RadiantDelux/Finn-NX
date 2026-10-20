#ifndef FINN_PATCHES_H
#define FINN_PATCHES_H
#include "so_util.h"
int dcr_guard_ok(so_module *, uint32_t, const uint32_t[4], const char *);
int dcr_hook(so_module *, uint32_t, const uint32_t[4], void *, const char *);
#endif
