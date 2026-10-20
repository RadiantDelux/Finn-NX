/* Touchscreen and a stick-driven pointer -> the original Unity Input API.
 * A clicks; X/Y/B and shoulders use the original game's actions.
 * Right-stick click sends Android Back; + Escape; - restarts the current run.
 * Event payloads match the shared Unity JNI getters (dcr_input.h). */
#include <math.h>
#include <stdlib.h>
#include <switch.h>
#include <GLES2/gl2.h>
#include "dcr_input.h"
#include "dcr_jni_unity.h"
#include "dcr_time.h"
#include "gl_layer.h"
#include "rt_pad.h"
#include "util.h"
#include "finn_controls.h"
#include "finn_display.h"
extern volatile int g_dcr_quit_requested;
static PadState pad;
static JObj *player;
static jboolean (*inject)(void *, void *, void *);
static float x = 640, y = 360;
static float contact_x, contact_y;
static int touching, cursor_visible;
static int64_t down_at;
static u64 last_tick, last_buttons;
const int dcr_pad_axes[] = {0, 1};
const int dcr_pad_naxes = 2;

static int action_mask(u64 buttons) {
    return ((buttons & HidNpadButton_Y) ? FINN_ACTION_KICK : 0) |
           ((buttons & HidNpadButton_X) ? FINN_ACTION_RECOVERY : 0) |
           ((buttons & HidNpadButton_B) ? FINN_ACTION_TAP : 0) |
           ((buttons & (HidNpadButton_L | HidNpadButton_ZL)) ? FINN_ACTION_LEFT : 0) |
           ((buttons & (HidNpadButton_R | HidNpadButton_ZR)) ? FINN_ACTION_RIGHT : 0) |
           ((buttons & HidNpadButton_Minus) ? FINN_ACTION_RESTART : 0);
}

static void motion(int action, float px, float py) {
    JObj *o = jni_new("android/view/MotionEvent");
    DcrMotion e = {0};
    e.action = action;
    e.count = 1;
    e.id[0] = 0;
    e.x[0] = px;
    e.y[0] = py;
    e.down_time_ms = down_at;
    e.event_time_ms = dcr_monotonic_ns() / 1000000ull;
    e.source = 0x1002;
    e.device_id = 0;
    o->p = &e;
    inject(g_jni_env, player, o);
    o->p = NULL;
    jni_release_obtained();
    jni_release(o);
}

static void key(int action, int code) {
    JObj *o = jni_new("android/view/KeyEvent");
    DcrKey e = {0};
    e.action = action;
    e.key_code = code;
    e.source = 0x101;
    e.event_time_ms = e.down_time_ms = dcr_monotonic_ns() / 1000000ull;
    o->p = &e;
    inject(g_jni_env, player, o);
    o->p = NULL;
    jni_release(o);
}

/* Merge rows with the same width: a small disk needs no shader/VBO state
 * changes, readback or allocation, and only a few scissored clears. */
static void cursor_disk(int cx, int cy, int radius) {
    int previous = -1, first = -radius;
    for (int row = -radius; row <= radius + 1; row++) {
        int span = row <= radius ? (int)sqrtf((float)(radius * radius - row * row)) : -1;
        if (span == previous)
            continue;
        if (previous >= 0) {
            glScissor(cx - previous, cy + first, previous * 2 + 1, row - first);
            glClear(GL_COLOR_BUFFER_BIT);
        }
        previous = span;
        first = row;
    }
}

static void cursor(void) {
    if (!cursor_visible)
        return;
    GLint fb, box[4];
    GLfloat color[4];
    GLboolean mask[4];
    GLboolean scissor = glIsEnabled(GL_SCISSOR_TEST);
    glGetIntegerv(GL_FRAMEBUFFER_BINDING, &fb);
    glGetIntegerv(GL_SCISSOR_BOX, box);
    glGetFloatv(GL_COLOR_CLEAR_VALUE, color);
    glGetBooleanv(GL_COLOR_WRITEMASK, mask);
    int w, h;
    dcr_window_size(&w, &h);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    glEnable(GL_SCISSOR_TEST);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    int radius = (h + 36) / 72;
    if (radius < 6)
        radius = 6;
    /* GUIAtlas's pink button fill is #ff5588, with a #660011 outline. */
    glClearColor(102.0f / 255, 0, 17.0f / 255, 1);
    cursor_disk((int)x, h - 1 - (int)y, radius);
    glClearColor(1, 85.0f / 255, 136.0f / 255, 1);
    cursor_disk((int)x, h - 1 - (int)y, radius - 1);
    glClearColor(color[0], color[1], color[2], color[3]);
    glColorMask(mask[0], mask[1], mask[2], mask[3]);
    glScissor(box[0], box[1], box[2], box[3]);
    if (!scissor)
        glDisable(GL_SCISSOR_TEST);
    glBindFramebuffer(GL_FRAMEBUFFER, fb);
}

void dcr_input_init(void) {
    rt_pad_setup(1, 1);
    padInitializeDefault(&pad);
    hidInitializeTouchScreen();
    player = jni_singleton("com/unity3d/player/UnityPlayer");
    inject = (void *)jni_native("com/unity3d/player/UnityPlayer", "nativeInjectEvent");
    dcr_present_hook = cursor;
    debugPrintf("[input] Y Jake, X recovery, B launch/repeat taps, L/ZL left penguins, R/ZR right; "
                "minus restart run, stick+A pointer, R-stick click back\n");
}

void dcr_input_frame(void) {
    if (!inject)
        return;
    padUpdate(&pad);
    u64 buttons = padGetButtons(&pad);
    u64 pressed = buttons & ~last_buttons, released = last_buttons & ~buttons;
    u64 now = armGetSystemTick();
    float dt = last_tick ? (float)armTicksToNs(now - last_tick) / 1e9f : 1.0f / 60;
    last_tick = now;
    if (dt > .05f)
        dt = .05f;
    HidAnalogStickState stick = padGetStickPos(&pad, 0);
    float sx = stick.x / 32767.0f, sy = stick.y / 32767.0f;
    if (fabsf(sx) < .15f)
        sx = 0;
    if (fabsf(sy) < .15f)
        sy = 0;
    int w, h;
    dcr_window_size(&w, &h);
    if (sx || sy) {
        x += sx * 800 * dt;
        y -= sy * 800 * dt;
        cursor_visible = 1;
    }
    /* Analog direction pseudo-buttons must not hide the pointer they move. */
    const u64 stick_directions = 0xffULL << 16;
    if (buttons & ~(HidNpadButton_A | stick_directions))
        cursor_visible = 0;
    if (x < 0)
        x = 0;
    if (x > w - 1)
        x = w - 1;
    if (y < 0)
        y = 0;
    if (y > h - 1)
        y = h - 1;
    HidTouchScreenState ts;
    int n = hidGetTouchScreenStates(&ts, 1);
    const u64 exit_combo = HidNpadButton_L | HidNpadButton_R | HidNpadButton_Plus;
    int quitting = (buttons & exit_combo) == exit_combo;
    int restarting = (buttons & HidNpadButton_Minus) != 0;
    if (restarting && touching) {
        motion(3, contact_x, contact_y);
        touching = 0;
    }
    int pulse = quitting ? 0 : finn_controls_tick(action_mask(pressed), action_mask(buttons));
    int active = n && ts.count;
    if (active) {
        x = ts.touches[0].x * (float)w / 1280;
        y = ts.touches[0].y * (float)h / 720;
        cursor_visible = 0;
    } else
        active = (buttons & HidNpadButton_A) != 0;
    if (restarting)
        active = 0;
    float px = x, py = y;
    if (!active && pulse && !touching) {
        active = 1;
        px = w * .5f;
        py = h * .3f;
    }
    if (active && !touching) {
        down_at = dcr_monotonic_ns() / 1000000ull;
        motion(0, px, py);
    } else if (active)
        motion(2, px, py);
    else if (touching)
        motion(1, contact_x, contact_y);
    if (active) {
        contact_x = px;
        contact_y = py;
    }
    touching = active;
    if (pressed & HidNpadButton_StickR)
        key(0, 4);
    if (released & HidNpadButton_StickR)
        key(1, 4);
    if (pressed & HidNpadButton_Plus)
        key(0, 111);
    if (released & HidNpadButton_Plus)
        key(1, 111);
    if (quitting)
        g_dcr_quit_requested = 1;
    last_buttons = buttons;
}

void finn_input_cancel(void) {
    if (touching && inject)
        motion(3, contact_x, contact_y);
    if (inject && (last_buttons & HidNpadButton_StickR))
        key(1, 4);
    if (inject && (last_buttons & HidNpadButton_Plus))
        key(1, 111);
    touching = 0;
    cursor_visible = 0;
    last_buttons = 0;
    last_tick = 0;
}
