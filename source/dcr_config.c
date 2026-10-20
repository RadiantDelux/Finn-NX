/* Configure the shared runtime; game rules and save values stay in the APK. */
#include "rt_cfg.h"
#include "util.h"
static const CfgOpt opts[] = {
    CFG_ROW_RESOLUTION("720", "Rendering resolution."),
    CFG_ROW_BOOST("Temporarily boost CPU during loading.", NULL),
    CFG_ROW_GL_SELFTEST(NULL),
    CFG_ROW_BOOT_LOG("Show startup diagnostics.", NULL),
    CFG_ROW_LOG_JNI("Trace Java calls when diagnosing a failed boot.", NULL),
};
static const CfgTable table = {.opts = opts, .nopts = CFG_COUNT(opts), .version = 1};

void dcr_config_load(void) {
    rt_config_load(&table);
}

int dcr_jitlog_on(void) {
    return 0;
}
