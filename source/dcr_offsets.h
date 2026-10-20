/* Generated from Finn Android 1.1.6 libmono.so; guarded before use. */
#ifndef FINN_MONO_OFFSETS_H
#define FINN_MONO_OFFSETS_H
#include <stdint.h>
#define DCR_MONO_RVA_FlushIcache 0x115768u
#define DCR_MONO_RVA_SuspendHandler 0x2e0530u
#define DCR_MONO_RVA_LookupThread 0x2df15cu
#define DCR_MONO_GOT_StopCount 0x3b8ba0u
#define DCR_MONO_GOT_AckSem 0x3b8d34u
#define DCR_MONO_GCT_SIGNAL 0xcu
#define DCR_MONO_GCT_LAST_STOP 0x10u
#define DCR_MONO_GCT_STACK_PTR 0x14u
#define DCR_MONO_GC_SUSPEND_SIG 0x1eu
#define DCR_MONO_GC_RESTART_SIG 0x18u
static const uint32_t DCR_MONO_GUARD_FlushIcache[4] = { 0xe92d0890u, 0xe28db008u, 0xe24dd014u, 0xe50b0018u };
static const uint32_t DCR_MONO_GUARD_SuspendHandler[4] = { 0xe92d4810u, 0xe28db008u, 0xe24dd01cu, 0xe59f4118u };
static const uint32_t DCR_MONO_GUARD_LookupThread[4] = { 0xe92d4810u, 0xe28db008u, 0xe24dd014u, 0xe59f305cu };
#endif
