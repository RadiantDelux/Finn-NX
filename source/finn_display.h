#ifndef FINN_DISPLAY_H
#define FINN_DISPLAY_H
#include "so_util.h"
int finn_display_install(so_module *module);
void finn_request_resize(void);
void finn_apply_window_resize(void);
void dcr_window_size(int *width, int *height);
#endif
