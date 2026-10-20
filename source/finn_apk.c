/* The same streaming APK check is compiled for the ARM32 game and launcher. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <switch.h>
#include "port_config.h"
#ifndef FINN_LAUNCHER
#include "util.h"
#define apk_log debugPrintf
#else
#define apk_log printf
#endif

int port_apk_check(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    unsigned char *buf = malloc(65536), digest[32];
    if (!buf) {
        fclose(f);
        return 0;
    }
    Sha256Context ctx;
    sha256ContextCreate(&ctx);
    size_t n;
    while ((n = fread(buf, 1, 65536, f)) != 0)
        sha256ContextUpdate(&ctx, buf, n);
    int ok = !ferror(f);
    if (fclose(f) != 0)
        ok = 0;
    free(buf);
    if (!ok) {
        apk_log("[apk] could not read all of %s\n", path);
        return 0;
    }
    sha256ContextGetHash(&ctx, digest);
    char hex[65];
    for (int i = 0; i < 32; i++)
        sprintf(hex + 2 * i, "%02x", digest[i]);
    ok = !strcmp(hex, PORT_APK_SHA256);
    apk_log("[apk] SHA-256 %s: %s (%s)\n", ok ? "OK" : "MISMATCH", hex, path);
    return ok;
}
