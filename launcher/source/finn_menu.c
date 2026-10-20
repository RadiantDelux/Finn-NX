/* Album/hbmenu hands off to the installed ARM32 application. */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <switch.h>
#include "dcr_exefs.h"
#include "rt_settings.h"
Result finn_install_forwarder(u64 *title_id);

/* Removing a HOME icon leaves title_id.txt and Atmosphere's override behind.
 * A launch request can be accepted before HOME discovers the missing title. */
static int system_has_forwarder(u64 tid) {
    bool installed = false;
    Result rc = nsInitialize();
    if (R_SUCCEEDED(rc)) {
        rc = nsIsAnyApplicationEntityInstalled(tid, &installed);
        nsExit();
    }
    FILE *log = fopen("sdmc:" PORT_ROOT_PATH "/forwarder-install.log", "a");
    if (log) {
        fprintf(log, "Finn HOME check %016lX: result 0x%x, installed %d\n", tid, (unsigned)rc,
                installed);
        fclose(log);
    }
    if (R_FAILED(rc))
        printf("Could not check Finn's HOME installation: 0x%x.\n", (unsigned)rc);
    return R_SUCCEEDED(rc) && installed;
}

static int installed_finn(u64 tid) {
    if (!exefs_is_forwarder_tid(tid))
        return 0;
    char path[128];
    snprintf(path, sizeof path, "sdmc:/atmosphere/contents/%016lX/exefs.nsp", tid);
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    if (fseek(f, 0, SEEK_END)) {
        fclose(f);
        return 0;
    }
    long len = ftell(f);
    if (len < 16 || len > 32 * 1024 * 1024 || fseek(f, 0, SEEK_SET)) {
        fclose(f);
        return 0;
    }
    uint8_t *buf = malloc((size_t)len);
    if (!buf) {
        fclose(f);
        return 0;
    }
    int ok = fread(buf, 1, (size_t)len, f) == (size_t)len;
    fclose(f);
    const uint8_t *npdm, *main;
    size_t size, main_size;
    u64 pid = 0;
    int is64 = 1;
    ok = ok && !exefs_find(buf, len, "main.npdm", &npdm, &size) &&
         !npdm_info(npdm, size, &pid, &is64) && pid == tid && !is64 &&
         !memcmp(npdm + 0x20, PORT_PAYLOAD_NAME, sizeof PORT_PAYLOAD_NAME) &&
         !exefs_find(buf, len, "main", &main, &main_size) && main_size >= 0x100 &&
         !memcmp(main, "NSO0", 4);
    free(buf);
    return ok && system_has_forwarder(tid);
}

int port_launcher_open_menu(void) {
    FILE *f = fopen("sdmc:" PORT_ROOT_PATH "/title_id.txt", "rb");
    char text[4096];
    size_t n = 0;
    if (f) {
        n = fread(text, 1, sizeof text - 1, f);
        fclose(f);
    }
    text[n] = 0;
    for (size_t i = 0; i + 16 <= n; i++) {
        if ((i && isxdigit((unsigned char)text[i - 1])) || isxdigit((unsigned char)text[i + 16]))
            continue;
        size_t k = 0;
        while (k < 16 && isxdigit((unsigned char)text[i + k]))
            k++;
        if (k != 16)
            continue;
        char hex[17];
        memcpy(hex, text + i, 16);
        hex[16] = 0;
        i += 15;
        u64 tid = strtoull(hex, 0, 16);
        if (!installed_finn(tid))
            continue;
        printf("\nLaunching Finn's installed ARM32 application (%016lX)...\n", tid);
        consoleUpdate(NULL);
        Result rc = appletRequestLaunchApplication(tid, NULL);
        if (R_SUCCEEDED(rc))
            return 1;
        printf("Existing forwarder launch failed: 0x%x. Trying Finn's automatic setup.\n",
               (unsigned)rc);
        break;
    }
    u64 tid = 0;
    Result rc = finn_install_forwarder(&tid);
    if (R_FAILED(rc)) {
        printf("See " PORT_ROOT_PATH
               "/forwarder-install.log, or use Install Forwarder in sphaira.\n");
        return 0;
    }
    if (!system_has_forwarder(tid)) {
        printf("Finn's HOME installation could not be confirmed. See " PORT_ROOT_PATH
               "/forwarder-install.log.\n");
        return 0;
    }
    printf("Starting Finn...\n");
    consoleUpdate(NULL);
    rc = appletRequestLaunchApplication(tid, NULL);
    if (R_SUCCEEDED(rc))
        return 1;
    printf("Finn is installed, but the launch request failed: 0x%x. Open its HOME icon.\n",
           (unsigned)rc);
    return 0;
}

void port_launcher_apk_help(void) {
    printf("\nCopy your Android 1.1.6 APK (any .apk filename) into " PORT_ROOT_PATH "/\n"
           "Required SHA-256: " PORT_APK_SHA256 "\n");
}
