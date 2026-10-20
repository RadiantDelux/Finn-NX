#include "dcr_setup.h"
#include "port_config.h"
static const char *const libs[] = {"libmain.so", "libunity.so", "libmono.so"};
const RtSetupPlan port_setup_plan = {
    .libs = libs,
    .nlibs = 3,
    .apk_requirement = "Use your own Jumping Finn Turbo 1.1.6 Android APK (armeabi-v7a).",
    .libs_p0 = 0,
    .libs_p1 = 800,
    .classes_p0 = 800,
    .classes_p1 = 1000,
};

const char *port_apk_help(void) {
    return "Place your Android 1.1.6 APK in /switch/finn_nx/ (any .apk filename).\n"
           "Required SHA-256: " PORT_APK_SHA256;
}
