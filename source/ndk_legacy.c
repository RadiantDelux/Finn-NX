/* Unity 4.3 also ships NativeActivity support. This port uses its Java view
 * lifecycle and nativeInjectEvent instead; no Android input queue is attached.
 * Keep the unused libmain NativeActivity imports well-defined, and redirect
 * Unity's glue helpers away from libmain's uninitialised Android activity. */
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include "bionic.h"
#include "imports.h"

typedef struct {
    int32_t type, device, action, key, meta, source;
    int64_t down, time;
    int count;
    float x[10], y[10];
} LegacyEvent;

int32_t b_AInputEvent_getSource(const LegacyEvent *e) {
    return e ? e->source : 0;
}

void b_AInputQueue_attachLooper(void *q, void *l, int id, void *cb, void *data) {}

void b_AInputQueue_detachLooper(void *q) {}

int b_AInputQueue_getEvent(void *q, void **event) {
    if (event)
        *event = NULL;
    return -1;
}

int b_AInputQueue_preDispatchEvent(void *q, void *event) {
    return 0;
}

void b_AInputQueue_finishEvent(void *q, void *event, int handled) {}

int32_t b_AMotionEvent_getAction(const LegacyEvent *e) {
    return e ? e->action : 0;
}

int64_t b_AMotionEvent_getDownTime(const LegacyEvent *e) {
    return e ? e->down : 0;
}

int64_t b_AMotionEvent_getEventTime(const LegacyEvent *e) {
    return e ? e->time : 0;
}

int32_t b_AMotionEvent_getEdgeFlags(const LegacyEvent *e) {
    return 0;
}

int32_t b_AMotionEvent_getFlags(const LegacyEvent *e) {
    return 0;
}

int32_t b_AMotionEvent_getMetaState(const LegacyEvent *e) {
    return e ? e->meta : 0;
}

size_t b_AMotionEvent_getPointerCount(const LegacyEvent *e) {
    return e ? (size_t)e->count : 0;
}

int32_t b_AMotionEvent_getPointerId(const LegacyEvent *e, size_t i) {
    return (int)i;
}

float b_AMotionEvent_getX(const LegacyEvent *e, size_t i) {
    return e && i < 10 ? e->x[i] : 0;
}

float b_AMotionEvent_getY(const LegacyEvent *e, size_t i) {
    return e && i < 10 ? e->y[i] : 0;
}

float b_AMotionEvent_getXPrecision(const LegacyEvent *e) {
    return 1;
}

float b_AMotionEvent_getYPrecision(const LegacyEvent *e) {
    return 1;
}

float b_AMotionEvent_getPressure(const LegacyEvent *e, size_t i) {
    return e ? 1 : 0;
}

float b_AMotionEvent_getSize(const LegacyEvent *e, size_t i) {
    return e ? 1 : 0;
}

float b_AMotionEvent_getOrientation(const LegacyEvent *e, size_t i) {
    return 0;
}

float b_AMotionEvent_getToolMajor(const LegacyEvent *e, size_t i) {
    return 1;
}

float b_AMotionEvent_getToolMinor(const LegacyEvent *e, size_t i) {
    return 1;
}

float b_AMotionEvent_getTouchMajor(const LegacyEvent *e, size_t i) {
    return 1;
}

float b_AMotionEvent_getTouchMinor(const LegacyEvent *e, size_t i) {
    return 1;
}

size_t b_AMotionEvent_getHistorySize(const LegacyEvent *e) {
    return 0;
}

int64_t b_AMotionEvent_getHistoricalEventTime(const LegacyEvent *e, size_t h) {
    return e ? e->time : 0;
}

float b_AMotionEvent_getHistoricalX(const LegacyEvent *e, size_t i, size_t h) {
    return b_AMotionEvent_getX(e, i);
}

float b_AMotionEvent_getHistoricalY(const LegacyEvent *e, size_t i, size_t h) {
    return b_AMotionEvent_getY(e, i);
}

float b_AMotionEvent_getHistoricalPressure(const LegacyEvent *e, size_t i, size_t h) {
    return b_AMotionEvent_getPressure(e, i);
}

float b_AMotionEvent_getHistoricalSize(const LegacyEvent *e, size_t i, size_t h) {
    return b_AMotionEvent_getSize(e, i);
}

int b___fpclassifyf(float x) {
    /* Android's libm uses bit values, not newlib's sequential FP_* enum:
     * infinity=1, NaN=2, normal=4, subnormal=8, zero=16. PhysX tests result&3
     * to reject non-finite values. Returning 2 for zero rejected identity
     * transforms, while returning 0 for NaN incorrectly accepted it.
     * Classify IEEE bits so the caller's FPSCR flush-to-zero mode is irrelevant.
     * AOSP android-4.3_r1/libm/include/math.h defines this ABI. */
    uint32_t bits;
    memcpy(&bits, &x, sizeof bits);
    bits &= 0x7fffffffu;
    if (!bits)
        return 0x10;
    if (bits >= 0x7f800000u)
        return bits == 0x7f800000u ? 0x01 : 0x02;
    return bits < 0x00800000u ? 0x08 : 0x04;
}

int b_pthread_attr_setschedpolicy(void *attr, int policy) {
    return 0;
}

int b_tkill(int tid, int sig);

int b_tgkill(int group, int tid, int sig) {
    return b_tkill(tid, sig);
}

static void *input_queue(void) {
    return NULL;
}

static void watchdog_feed(double value) {}

static void watchdog_enable(int value) {}

static void first_level(int value) {}

static void forward_event(void *event, void *env) {}

const DynLibFunction port_imports[] = {
    {"_Z29ANativeActivity_getInputQueuev", (uintptr_t)input_queue},
    {"_Z28ANativeActivity_feedWatchdogd", (uintptr_t)watchdog_feed},
    {"_Z30ANativeActivity_enableWatchdogb", (uintptr_t)watchdog_enable},
    {"_Z42ANativeActivity_setFirstLevelHasBeenLoadedb", (uintptr_t)first_level},
    {"_Z42ANativeActivity_forwardMotionEventToDalvikP11AInputEventP7_JNIEnv",
     (uintptr_t)forward_event},
};
const int port_imports_count = sizeof port_imports / sizeof port_imports[0];
