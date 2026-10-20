#include <assert.h>
#include <stdio.h>
#include "dcr_exefs.h"

int main(void) {
    uint8_t pfs[96] = {0};
    memcpy(pfs, "PFS0", 4);
    exefs_wr32(pfs + 4, 1);
    exefs_wr32(pfs + 8, 8);
    memcpy(pfs + 40, "main", 5);
    exefs_wr64(pfs + 24, 8);
    const uint8_t *data;
    const char *name;
    size_t size;
    assert(exefs_file(pfs, sizeof pfs, 0, &name, &data, &size) == 0);
    assert(size == 8 && data == pfs + 48 && strcmp(name, "main") == 0);
    exefs_wr64(pfs + 16, UINT64_MAX - 47);
    assert(exefs_file(pfs, sizeof pfs, 0, &name, &data, &size) == -1);
    exefs_wr64(pfs + 16, 0);
    exefs_wr64(pfs + 24, UINT64_MAX - 47);
    assert(exefs_file(pfs, sizeof pfs, 0, &name, &data, &size) == -1);
    exefs_wr32(pfs + 32, 8);
    assert(exefs_file(pfs, sizeof pfs, 0, &name, &data, &size) == -1);

    uint8_t npdm[0x400] = {0};
    memcpy(npdm, "META", 4);
    exefs_wr32(npdm + 0x70, 0x80);
    exefs_wr32(npdm + 0x78, 0x100);
    memcpy(npdm + 0x80, "ACI0", 4);
    memcpy(npdm + 0x300, "ACID", 4);
    exefs_wr64(npdm + 0x90, 0x059669A728222000ULL);
    uint64_t id;
    int is64;
    assert(npdm_info(npdm, sizeof npdm, &id, &is64) == 0 && !is64);
    assert(id == 0x059669A728222000ULL);
    exefs_wr32(npdm + 0x70, UINT32_MAX - 8);
    assert(npdm_info(npdm, sizeof npdm, &id, &is64) == -1);
    exefs_wr32(npdm + 0x70, 0x80);
    exefs_wr32(npdm + 0x78, UINT32_MAX - 8);
    assert(npdm_info(npdm, sizeof npdm, &id, &is64) == -1);
    puts("PASS: valid ExeFS/NPDM and overflowing offsets/sizes");
    return 0;
}
