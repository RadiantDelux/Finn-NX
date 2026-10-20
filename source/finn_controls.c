/* Invoke our helper on UnityMain after the game's Mono has started. */
#include <stdint.h>
#include <string.h>
#include "so_util.h"
#include "util.h"
#include "finn_controls.h"
#include "finn_controls_assembly.h"
extern so_module mono_mod;
static void *(*root_domain)(void), *(*thread_current)(void);
static void (*assembly_foreach)(void (*)(void *, void *), void *);
static void *(*assembly_image)(void *);
static const char *(*image_name)(void *);
static void *(*image_open)(char *, uint32_t, int, int *, int);
static void *(*assembly_load)(void *, const char *, int *, int);
static void *(*class_from_name)(void *, const char *, const char *);
static void *(*method_from_name)(void *, const char *, int);
static void *(*invoke)(void *, void *, void **, void **);
static void *(*unbox)(void *);
static void *tick;
static int bound, failed;

static void game_assembly(void *assembly, void *found) {
    const char *name = image_name(assembly_image(assembly));
    if (name && (!strcmp(name, "Assembly-CSharp") || !strcmp(name, "Assembly-CSharp.dll")))
        *(int *)found = 1;
}

static int bind(void) {
    if (bound)
        return !failed;
    bound = 1;
#define BIND(var, name)                                                                            \
    do {                                                                                           \
        *(void **)(&var) = (void *)so_try_find_addr_rx(&mono_mod, name);                           \
        if (!var)                                                                                  \
            failed = 1;                                                                            \
    } while (0)
    BIND(root_domain, "mono_get_root_domain");
    BIND(thread_current, "mono_thread_current");
    BIND(assembly_foreach, "mono_assembly_foreach");
    BIND(assembly_image, "mono_assembly_get_image");
    BIND(image_name, "mono_image_get_name");
    BIND(image_open, "mono_image_open_from_data_full");
    BIND(assembly_load, "mono_assembly_load_from_full");
    BIND(class_from_name, "mono_class_from_name");
    BIND(method_from_name, "mono_class_get_method_from_name");
    BIND(invoke, "mono_runtime_invoke");
    BIND(unbox, "mono_object_unbox");
#undef BIND
    if (failed)
        debugPrintf("[input] managed controls unavailable: Mono API missing\n");
    return !failed;
}

int finn_controls_tick(int down, int held) {
    if ((!down && !held) || failed || !bind())
        return 0;
    if (!root_domain() || !thread_current())
        return 0;
    if (!tick) {
        int loaded = 0;
        assembly_foreach(game_assembly, &loaded);
        if (!loaded)
            return 0;
        int status = 0;
        void *image = image_open((char *)finn_controls_assembly, sizeof finn_controls_assembly, 1,
                                 &status, 0);
        void *assembly = image ? assembly_load(image, "FinnControls.dll", &status, 0) : 0;
        void *cls = assembly ? class_from_name(image, "", "FinnControls") : 0;
        tick = cls ? method_from_name(cls, "Tick", 2) : 0;
        if (!tick) {
            failed = 1;
            debugPrintf("[input] could not load managed controls (Mono status %d)\n", status);
            return 0;
        }
        debugPrintf("[input] original actions connected: Y Jake, X recovery, B launch/tap, L/ZL "
                    "left, R/ZR right, minus restart run\n");
    }
    void *args[] = {&down, &held}, *exc = 0;
    void *result = invoke(tick, 0, args, &exc);
    if (exc) {
        failed = 1;
        debugPrintf("[input] managed controls raised an exception; pointer remains available\n");
        return 0;
    }
    return result ? *(int *)unbox(result) : 0;
}
