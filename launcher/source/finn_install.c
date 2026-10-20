/* Install only Finn's own homebrew forwarder, then let the menu hand off.
 * NCA/CNMT layouts: switchbrew.org. No tickets or commercial program data.
 * The console's SPL service encrypts headers; derived keys are never saved.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <switch.h>
#include "dcr_exefs.h"
#include "rt_settings.h"
#include "finn_auto_assets.h"

#define INSTALL_ERROR MAKERESULT(Module_Libnx, LibnxError_BadInput)
#define ROOT "sdmc:" PORT_ROOT_PATH

typedef struct {
    u8 *data;
    size_t size;
    u8 hash[32];
    NcmContentInfo info;
} AutoNca;

typedef struct {
    NcmContentMetaHeader header;
    NcmApplicationMetaExtendedHeader extended;
    NcmContentInfo info[3];
} AutoMeta;

typedef struct {
    NcmContentMetaKey key;
    u8 storage;
    u8 pad[7];
} AutoRecord;

_Static_assert(sizeof(AutoMeta) == 96, "NCM metadata layout");
_Static_assert(sizeof(AutoRecord) == 24, "NS application record layout");

static const u8 kek_source[16] = {0x1f, 0x12, 0x91, 0x3a, 0x4a, 0xcb, 0xf0, 0x0d,
                                  0x4c, 0xde, 0x3a, 0xf6, 0xd5, 0x23, 0x88, 0x2a};
static const u8 key_source[32] = {0x5a, 0x3e, 0xd8, 0x4f, 0xde, 0xc0, 0xd8, 0x26, 0x31, 0xf7, 0xe2,
                                  0x5d, 0x19, 0x7b, 0xf5, 0xd0, 0x1c, 0x9b, 0x7b, 0xfa, 0xf6, 0x28,
                                  0x18, 0x3d, 0x71, 0xf6, 0x4d, 0x73, 0xf1, 0x50, 0xb9, 0xd2};

static u8 *read_all(const char *path, size_t *size) {
    *size = 0;
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END)) {
        fclose(f);
        return NULL;
    }
    long n = ftell(f);
    if (n <= 0 || n > 32 * 1024 * 1024 || fseek(f, 0, SEEK_SET)) {
        fclose(f);
        return NULL;
    }
    u8 *b = malloc(n);
    if (!b || fread(b, 1, n, f) != (size_t)n) {
        free(b);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *size = n;
    return b;
}

static Result load_nca(AutoNca *n, const char *path, const u8 expected[32], u8 type) {
    n->data = read_all(path, &n->size);
    if (!n->data || n->size < 0xc00)
        return INSTALL_ERROR;
    u8 hash[32];
    sha256CalculateHash(hash, n->data, n->size);
    if (memcmp(hash, expected, 32) || memcmp(n->data + 0x200, "NCA3", 4) ||
        exefs_rd64(n->data + 0x208) != n->size ||
        exefs_rd64(n->data + 0x210) != FINN_AUTO_TITLE_ID || n->data[0x205] != type)
        return INSTALL_ERROR;
    return 0;
}

static void seal_nca(AutoNca *n, const u8 key[32], NcmContentType type) {
    Aes128XtsContext ctx;
    aes128XtsContextCreate(&ctx, key, key + 16, true);
    for (unsigned i = 0; i < 6; i++) {
        aes128XtsContextResetSector(&ctx, i, true);
        aes128XtsEncrypt(&ctx, n->data + i * 512, n->data + i * 512, 512);
    }
    sha256CalculateHash(n->hash, n->data, n->size);
    memcpy(&n->info.content_id, n->hash, 16);
    n->info.content_type = type;
    ncmU64ToContentInfoSize(n->size, &n->info);
    memset(&ctx, 0, sizeof ctx);
}

/* Patch the two packaged content infos and rehash the metadata template. */
static Result finish_meta(AutoNca ncas[3], size_t *cnmt_size) {
    AutoNca *n = &ncas[2];
    u8 *h = n->data, *fs = h + 0x400;
    size_t sec = (size_t)exefs_rd32(h + 0x240) * 512, pfs_off = exefs_rd64(fs + 0x40),
           pfs_size = exefs_rd64(fs + 0x48);
    if (sec + pfs_off + pfs_size > n->size || exefs_rd64(fs + 0x38) != 32 || pfs_size > 0x1000)
        return INSTALL_ERROR;
    char name[40];
    snprintf(name, sizeof name, "Application_%016llX.cnmt", (unsigned long long)FINN_AUTO_TITLE_ID);
    const u8 *p;
    size_t size;
    if (exefs_find(h + sec + pfs_off, pfs_size, name, &p, &size) || size != 192 ||
        exefs_rd64(p) != FINN_AUTO_TITLE_ID)
        return INSTALL_ERROR;
    u8 *cnmt = (u8 *)p;
    for (int i = 0; i < 2; i++) {
        memcpy(cnmt + 48 + i * 56, ncas[i].hash, 32);
        memcpy(cnmt + 80 + i * 56, &ncas[i].info, sizeof(NcmContentInfo));
    }
    sha256CalculateHash(cnmt + size - 32, cnmt, size - 32);
    sha256CalculateHash(h + sec, h + sec + pfs_off, pfs_size);
    sha256CalculateHash(fs + 8, h + sec, 32);
    sha256CalculateHash(h + 0x280, fs, 512);
    *cnmt_size = size;
    return 0;
}

static Result register_nca(NcmContentStorage *cs, const AutoNca *n) {
    bool present = false;
    Result rc = ncmContentStorageHas(cs, &present, &n->info.content_id);
    if (R_FAILED(rc) || present)
        return rc;
    NcmPlaceHolderId id;
    rc = ncmContentStorageGeneratePlaceHolderId(cs, &id);
    if (R_FAILED(rc))
        return rc;
    rc = ncmContentStorageCreatePlaceHolder(cs, &n->info.content_id, &id, n->size);
    if (R_FAILED(rc))
        return rc;
    for (size_t off = 0; off < n->size && R_SUCCEEDED(rc); off += 0x10000) {
        size_t count = n->size - off;
        if (count > 0x10000)
            count = 0x10000;
        rc = ncmContentStorageWritePlaceHolder(cs, &id, off, n->data + off, count);
    }
    if (R_SUCCEEDED(rc))
        rc = ncmContentStorageFlushPlaceHolder(cs);
    if (R_SUCCEEDED(rc))
        rc = ncmContentStorageRegister(cs, &n->info.content_id, &id);
    if (R_FAILED(rc))
        ncmContentStorageDeletePlaceHolder(cs, &id);
    return rc;
}

/* An existing record may only be repaired if its program content is ours.
 * The small forwarder program is stable across port updates. */
static Result check_owner(NcmContentMetaDatabase *db, const NcmContentId *program) {
    s32 total = 0, written = 0;
    NcmContentMetaKey key;
    Result rc = ncmContentMetaDatabaseList(
        db, &total, &written, &key, 1, NcmContentMetaType_Application, FINN_AUTO_TITLE_ID,
        FINN_AUTO_TITLE_ID, FINN_AUTO_TITLE_ID, NcmContentInstallType_Full);
    if (R_FAILED(rc) || !total)
        return rc;
    if (total != 1 || written != 1 || key.id != FINN_AUTO_TITLE_ID || key.version != 0)
        return INSTALL_ERROR;
    NcmContentId installed;
    rc = ncmContentMetaDatabaseGetContentIdByType(db, &installed, &key, NcmContentType_Program);
    if (R_FAILED(rc))
        return rc;
    return memcmp(&installed, program, 16) ? INSTALL_ERROR : 0;
}

static int own_override(const u8 *b, size_t len) {
    const u8 *npdm;
    size_t size;
    u64 tid;
    int is64;
    return !exefs_find(b, len, "main.npdm", &npdm, &size) && !npdm_info(npdm, size, &tid, &is64) &&
           tid == FINN_AUTO_TITLE_ID && !is64 &&
           !memcmp(npdm + 0x20, PORT_PAYLOAD_NAME, sizeof PORT_PAYLOAD_NAME);
}

/* Never overwrite another program. Existing valid Finn overrides update
 * themselves from the NRO through the already-tested runtime update path. */
static Result prepare_override(void) {
    char dir[100], path[128], tmp[144];
    snprintf(dir, sizeof dir, "sdmc:/atmosphere/contents/%016llX",
             (unsigned long long)FINN_AUTO_TITLE_ID);
    snprintf(path, sizeof path, "%s/exefs.nsp", dir);
    snprintf(tmp, sizeof tmp, "%s.finn-part", path);
    size_t n = 0;
    u8 *cur = read_all(path, &n);
    if (cur) {
        int ours = own_override(cur, n);
        free(cur);
        return ours ? 0 : INSTALL_ERROR;
    }
    struct stat st;
    if (!stat(path, &st))
        return INSTALL_ERROR;
    u8 *program = read_all("romfs:/" PORT_NSP_NAME, &n), *override = NULL;
    size_t override_size = 0;
    if (!program ||
        exefs_build_override(program, n, FINN_AUTO_TITLE_ID, &override, &override_size)) {
        free(program);
        return INSTALL_ERROR;
    }
    free(program);
    mkdir("sdmc:/atmosphere", 0777);
    mkdir("sdmc:/atmosphere/contents", 0777);
    mkdir(dir, 0777);
    FILE *f = fopen(tmp, "wb");
    if (!f) {
        free(override);
        return INSTALL_ERROR;
    }
    int ok = fwrite(override, 1, override_size, f) == override_size;
    if (fflush(f))
        ok = 0;
    if (fclose(f))
        ok = 0;
    free(override);
    if (ok)
        ok = rename(tmp, path) == 0;
    if (!ok)
        remove(tmp);
    return ok ? 0 : INSTALL_ERROR;
}

static Result publish(Service *ns, const NcmContentMetaKey *key) {
    AutoRecord record = {.key = *key, .storage = NcmStorageId_SdCard};

    struct {
        u8 event;
        u8 pad[7];
        u64 id;
    } in = {.event = 3, .id = FINN_AUTO_TITLE_ID};

    return serviceDispatchIn(ns, 16, in,
                             .buffer_attrs = {SfBufferAttr_HipcMapAlias | SfBufferAttr_In},
                             .buffers = {{&record, sizeof record}});
}

Result finn_install_forwarder(u64 *title_id) {
    Result rc = 0;
    const char *phase = "validating templates";
    AutoNca ncas[3] = {0};
    u8 key[32] = {0}, sealed_kek[16] = {0};
    bool ncm = false, ns = false, spl = false;
    NcmContentStorage cs = {0};
    NcmContentMetaDatabase db = {0};
    Service manager = {0};
    size_t cnmt_size = 0;
    NcmContentMetaKey meta_key = {.id = FINN_AUTO_TITLE_ID,
                                  .version = 0,
                                  .type = NcmContentMetaType_Application,
                                  .install_type = NcmContentInstallType_Full};
#define STEP(label, call)                                                                          \
    do {                                                                                           \
        phase = label;                                                                             \
        rc = (call);                                                                               \
        if (R_FAILED(rc))                                                                          \
            goto done;                                                                             \
    } while (0)
    printf("\nCreating Finn's HOME forwarder (%016llX)...\n",
           (unsigned long long)FINN_AUTO_TITLE_ID);
    consoleUpdate(NULL);
    STEP("program template",
         load_nca(&ncas[0], "romfs:/finn-auto-program.nca", finn_auto_program_sha, 0));
    STEP("control template",
         load_nca(&ncas[1], "romfs:/finn-auto-control.nca", finn_auto_control_sha, 2));
    STEP("metadata template",
         load_nca(&ncas[2], "romfs:/finn-auto-meta.nca", finn_auto_meta_sha, 1));
    STEP("NCM service", ncmInitialize());
    ncm = true;
    STEP("NS service", nsInitialize());
    ns = true;
    STEP("application manager", nsGetApplicationManagerInterface(&manager));
    STEP("SPL crypto service", splCryptoInitialize());
    spl = true;
    STEP("header KEK", splCryptoGenerateAesKek(kek_source, 0, 0, sealed_kek));
    STEP("header encryption key", splCryptoGenerateAesKey(sealed_kek, key_source, key));
    STEP("header encryption key", splCryptoGenerateAesKey(sealed_kek, key_source + 16, key + 16));
    seal_nca(&ncas[0], key, NcmContentType_Program);
    seal_nca(&ncas[1], key, NcmContentType_Control);
    STEP("metadata hashes", finish_meta(ncas, &cnmt_size));
    seal_nca(&ncas[2], key, NcmContentType_Meta);
    STEP("SD content storage", ncmOpenContentStorage(&cs, NcmStorageId_SdCard));
    STEP("SD metadata database", ncmOpenContentMetaDatabase(&db, NcmStorageId_SdCard));
    STEP("forwarder identity", check_owner(&db, &ncas[0].info.content_id));
    printf("Installing Finn's program and icon...\n");
    consoleUpdate(NULL);
    for (int i = 0; i < 3; i++)
        STEP("content registration", register_nca(&cs, &ncas[i]));
    AutoMeta metadata = {0};
    metadata.header.extended_header_size = sizeof metadata.extended;
    metadata.header.content_count = 3;
    metadata.extended.patch_id = FINN_AUTO_TITLE_ID | 0x800;
    metadata.info[0] = ncas[2].info;
    ncmU64ToContentInfoSize(cnmt_size, &metadata.info[0]);
    metadata.info[1] = ncas[0].info;
    metadata.info[2] = ncas[1].info;
    STEP("metadata registration",
         ncmContentMetaDatabaseSet(&db, &meta_key, &metadata, sizeof metadata));
    STEP("metadata commit", ncmContentMetaDatabaseCommit(&db));
    STEP("ARM32 program preparation", prepare_override());
    STEP("HOME application record", publish(&manager, &meta_key));
    /* Cache refresh is advisory; installation is already committed. */
    serviceDispatchIn(&manager, 404, meta_key.id);
    *title_id = FINN_AUTO_TITLE_ID;
done:
    memset(key, 0, sizeof key);
    memset(sealed_kek, 0, sizeof sealed_kek);
    ncmContentMetaDatabaseClose(&db);
    ncmContentStorageClose(&cs);
    serviceClose(&manager);
    if (spl)
        splCryptoExit();
    if (ns)
        nsExit();
    if (ncm)
        ncmExit();
    for (int i = 0; i < 3; i++)
        free(ncas[i].data);
    FILE *log = fopen(ROOT "/forwarder-install.log", "a");
    if (log) {
        fprintf(log, "Finn auto-forwarder %016llX: %s, result 0x%x\n",
                (unsigned long long)FINN_AUTO_TITLE_ID, R_SUCCEEDED(rc) ? "installed" : phase,
                (unsigned)rc);
        fclose(log);
    }
    if (R_FAILED(rc))
        printf("Automatic installation failed at %s: 0x%x.\n", phase, (unsigned)rc);
    else
        printf("Finn's HOME forwarder is installed.\n");
#undef STEP
    return rc;
}
