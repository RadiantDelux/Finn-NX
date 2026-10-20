/* Jumping Finn Turbo 1.1.6, Unity 4.3.0f4, Android ARMv7. */
#ifndef PORT_CONFIG_H
#define PORT_CONFIG_H
#define PORT_TITLE "Jumping Finn Turbo"
#define PORT_NAME "finn_nx"
#define PORT_PACKAGE "com.turner.jft"
#define PORT_BANNER "Finn NX " FINN_VERSION ": Unity 4.3.0f4 / Mono / AArch32 / OpenGL ES"
#define PORT_APK_DESC "Jumping Finn Turbo 1.1.6, Android armeabi-v7a"
#define PORT_APK_SHA256 "7b3c4d0058c8f613b0a696fbbdd96b4fd0162e75d3ee85da11d9f38cf768d040"
#define PORT_APK_ROLES {.what = "the game (SHA-256 verified)", .check = port_apk_check}
#define PORT_SO_REGION_BYTES (48u * 1024 * 1024)
#define PORT_LAUNCHER_START_NOTE "Place your Android APK beside finn_nx.nro."
#define RT_PROC_COMM "jumpingfinn"
#define RT_EXTRA_ENV "MONO_DEBUG=explicit-null-checks"
#define RT_DL_HAS_OPENSLES 0
#define RT_OPENSLES 0
#define RT_JNI_UNHANDLED_INSTANCE_SINGLETON 1
#define RT_JNI_UNHANDLED_BUILDER_RETURNS_SELF 1
#define RT_LOOPER_MAIN_IMPLICIT 0
#define RT_GL_SWAP_ENDS_FRAME 0
#define RT_MAIN_THREAD_NAME "UnityMain"
#define RT_PATH_CWD_RELATIVE 0
#define RT_DIRCACHE 0
#define RT_PACKAGE_MISMATCH_FATAL 1
#define RT_MANIFEST_LOG_PREFIX "finn"
#define RT_WATCHDOG_BOOT 1
/* Unity 4.3's APK reader exits if woken while its job queue is empty. */
#define RT_COND_SPURIOUS_POLL 0
#define RT_LOG_THREAD_CREATE 1
#endif
