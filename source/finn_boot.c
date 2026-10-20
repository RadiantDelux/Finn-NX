/* Host Unity 4.3's actual JNI lifecycle, using the APK's engine and scripts.
 * The surface native has ONE Java argument in 4.3 (5.6 has two).
 * libmain is loaded for dependencies; its NativeActivity glue is replaced by
 * the UnityPlayer view lifecycle and Switch input, as allowed by this player. */
#include <stdio.h>
#include <string.h>
#include <switch.h>
#include "config.h"
#include "dcr_boost.h"
#include "dcr_input.h"
#include "dcr_jni_unity.h"
#include "dcr_manifest.h"
#include "dcr_path.h"
#include "dcr_setup.h"
#include "error.h"
#include "finn_display.h"
#include "gl_layer.h"
#include "imports.h"
#include "jit_arena.h"
#include "rt_applet.h"
#include "rt_cfg.h"
#include "so_util.h"
#include "util.h"
#include "watchdog.h"

so_module main_mod, unity_mod, mono_mod;
extern volatile int g_dcr_quit_requested;
int dcr_mono_install(void);
void dcr_mono_hook_exceptions(void);
void dcr_audio_fmod_start(JObj *device);
void dcr_audio_fmod_stop(void);
void dcr_audio_selftest(void);
void dcr_jit_emu_frame_end(void);

void __attribute__((noreturn)) dcr_emu_stray(uint32_t *regs) {
    debugPrintf("[jit] execution reached an unallocated JIT page (lr=%08lx)\n",
                (unsigned long)regs[13]);
    fatal_error("Mono jumped outside its generated code. See debug.log.");
}

typedef void (*CtxFn)(void *, void *, void *);
typedef void (*UnityVoidFn)(void *, void *);
typedef jboolean (*BoolFn)(void *, void *);
typedef void (*FocusFn)(void *, void *, jboolean);

static struct {
    CtxFn init, file, recreate, www;
    UnityVoidFn resume, done;
    BoolFn render, pause;
    FocusFn focus, forward;
    void (*resize)(void *, void *, jint, jint, jint, jint);
    void (*display)(void *, void *, jint);
    void (*orientation)(void *, void *, jint);
} U;

static JObj *player;
static volatile int resize_pending;
static uint64_t frames;

uint64_t dcr_boot_frames(void) {
    return frames;
}

void port_audio_selftest(void) {
    dcr_audio_selftest();
}

static int load(so_module *m, const char *name) {
    char p[512];
    snprintf(p, sizeof p, "%s/%s", dcr_game_root(), name);
    int rc = so_load(m, p, NULL, PORT_SO_REGION_BYTES);
    if (rc < 0) {
        debugPrintf("[finn] load %s failed: %d\n", name, rc);
        return -1;
    }
    so_relocate(m);
    return 0;
}

int port_load(const char *apk) {
    if (strcmp(dcr_manifest_version_name(), "1.1.6"))
        fatal_error("This build targets Android version 1.1.6; found %s.",
                    dcr_manifest_version_name());
    dcr_setup_from_apk(apk);
    if (load(&main_mod, DCR_LIB_MAIN) || load(&unity_mod, DCR_LIB_UNITY) ||
        load(&mono_mod, DCR_LIB_MONO))
        fatal_error("Could not load the ARMv7 libraries. See debug.log.");
    so_module *mods[] = {&main_mod, &unity_mod, &mono_mod};
    int missing = 0;
    for (unsigned i = 0; i < 3; i++)
        missing += so_resolve(mods[i], dcr_imports, dcr_imports_count, 1);
    if (missing)
        fatal_error("%d unresolved Android imports. See debug.log.", missing);
    /* This Unity links old libgcc atomics which branch to Linux's fixed kuser
     * page (0xffff0fc0 / 0xffff0fa0). Horizon has no such page. Rewrite the
     * literals while each image is still writable, before any constructor runs. */
    for (unsigned i = 0; i < 3; i++)
        if (so_fix_kuser_helpers(mods[i]) < 0)
            fatal_error("Could not redirect Android atomic helpers in %s.", mods[i]->base_name);
    if (!finn_display_install(&unity_mod))
        fatal_error("The Unity display configuration does not match this APK build.");
    for (unsigned i = 0; i < 3; i++) {
        so_finalize(mods[i]);
        so_flush_caches(mods[i]);
    }
    if (jit_arena_init() != 0)
        fatal_error("Could not allocate executable memory for Mono.");
    if (!dcr_mono_install())
        fatal_error("The Mono library does not match the verified APK build.");
    dcr_mono_hook_exceptions();
    return 0;
}

static void *native(const char *name, int required) {
    void *fn = jni_native("com/unity3d/player/UnityPlayer", name);
    debugPrintf("[finn] %-26s %p\n", name, fn);
    if (!fn && required)
        fatal_error("Required Unity 4.3 native %s is missing.", name);
    return fn;
}

void port_focus_lost(void) {
    finn_input_cancel();
    if (U.focus)
        U.focus(g_jni_env, player, 0);
    if (U.pause)
        U.pause(g_jni_env, player);
    dcr_audio_fmod_stop();
}

void port_focus_gained(void) {
    if (U.resume)
        U.resume(g_jni_env, player);
    if (U.focus)
        U.focus(g_jni_env, player, 1);
    /* UnityPlayer.g()/pause() in this APK start/stop FMOD's Java thread.
     * Calling the engine JNI lifecycle directly does not run that Java code. */
    dcr_audio_fmod_start(jni_singleton("org/fmod/FMODAudioDevice"));
}

void finn_request_resize(void) {
    resize_pending = 1;
}

void finn_apply_window_resize(void) {
    int w, h;
    dcr_window_size(&w, &h);
    if (w <= 0 || h <= 0)
        fatal_error("Invalid game window dimensions: %d x %d.", w, h);
    resize_pending = 0;
    /* Unity 4.3 divides width/arg3 and height/arg4. These are surface and
     * logical dimensions, NOT Android pixel format and display rotation. */
    U.resize(g_jni_env, player, w, h, w, h);
    debugPrintf("[display] nativeResize(%d, %d, %d, %d): scale 1 x 1\n", w, h, w, h);
}

void port_run(void) {
    so_execute_init_array(&main_mod);
    so_execute_init_array(&unity_mod);
    so_execute_init_array(&mono_mod);
    jni_init();
    jni_looper_bind_engine();
    dcr_watchdog_start();
    typedef jint (*OnLoad)(void *, void *);
    OnLoad onload = (OnLoad)so_try_find_addr_rx(&unity_mod, "JNI_OnLoad");
    if (!onload || onload(g_jni_vm, NULL) != JNI_VERSION_1_6)
        fatal_error("Unity JNI registration failed. See debug.log.");
    U.init = (CtxFn)native("initJni", 1);
    U.file = (CtxFn)native("nativeFile", 1);
    U.recreate = (CtxFn)native("nativeRecreateGfxState", 1);
    U.www = (CtxFn)native("nativeInitWWW", 0);
    U.resume = (UnityVoidFn)native("nativeResume", 1);
    U.done = (UnityVoidFn)native("nativeDone", 0);
    U.render = (BoolFn)native("nativeRender", 1);
    U.pause = (BoolFn)native("nativePause", 0);
    U.focus = (FocusFn)native("nativeFocusChanged", 0);
    U.forward = (FocusFn)native("nativeForwardEventsToDalvik", 0);
    U.resize = (void *)native("nativeResize", 1);
    U.display = (void *)native("nativeSetDefaultDisplay", 0);
    U.orientation = (void *)native("nativeDeviceOrientation", 0);
    player = jni_singleton("com/unity3d/player/UnityPlayer");
    JObj *ctx = jni_singleton("com/turner/jft/UnityPlayerNativeActivity");
    debugPrintf("[finn] initJni\n");
    U.init(g_jni_env, player, ctx);
    JObj *ap = jni_str(DCR_ANDROID_APK);
    U.file(g_jni_env, player, ap);
    jni_release(ap);
    if (U.www)
        U.www(g_jni_env, player, jni_class("com/unity3d/player/WWW")->obj);
    if (U.display)
        U.display(g_jni_env, player, 0);
    if (U.forward)
        U.forward(g_jni_env, player, 0);
    finn_apply_window_resize();
    U.recreate(g_jni_env, player, jni_singleton("android/view/Surface"));
    if (U.orientation)
        U.orientation(g_jni_env, player, 3);
    dcr_input_init();
    port_focus_gained();
    debugPrintf("[finn] entering original game's frame loop\n");
    while (appletMainLoop() && !g_dcr_quit_requested) {
        rt_applet_poll();
        if (!rt_focused()) {
            svcSleepThread(50000000ll);
            continue;
        }
        dcr_input_frame();
        jni_looper_run_engine();
        /* A callback from inside nativeRender must be deferred until that JNI
         * call has returned; Unity's JNI guard disallows nested native calls. */
        if (resize_pending)
            finn_apply_window_resize();
        dcr_boost_frame_begin();
        if (!U.render(g_jni_env, player))
            break;
        dcr_jit_emu_frame_end();
        frames++;
        dcr_boost_frame_end(frames);
        if (dcr_gl_frames() == 1)
            dcr_boost_first_picture();
        dcr_boost_launch_tick();
        if (frames % 60 == 0)
            log_console_update();
        if (frames <= 3 || frames % 600 == 0)
            debugPrintf("[finn] engine frame %llu, presented %lu\n", (unsigned long long)frames,
                        (unsigned long)dcr_gl_frames());
    }
    dcr_audio_fmod_stop();
    if (U.done)
        U.done(g_jni_env, player);
}
