#!/usr/bin/env bash
# Called by build.ps1 after validating the APK and preparing dependencies.
set -euo pipefail

root=$(cygpath -u "$1")
dkp=$(cygpath -u "$2")
cache=$(cygpath -u "$3")
cd "$root"
export DEVKITPRO="$dkp" DEVKITARM="$dkp/devkitARM" DEVKITA64="$dkp/devkitA64"
export PATH="$DEVKITARM/bin:$dkp/tools/bin:/usr/bin:$PATH"
mkdir -p build/miniz portlibs32/include/miniz portlibs32/lib launcher/romfs
cp -pR "$cache/mesa32/mesa32/include/." portlibs32/include/
cp -p "$cache/mesa32/mesa32/lib/"*.a portlibs32/lib/
cp -p vendor/miniz/*.h portlibs32/include/miniz/

changed=0
for name in miniz miniz_tdef miniz_tinfl miniz_zip; do
    if [[ ! -f "build/miniz/$name.o" || "vendor/miniz/$name.c" -nt "build/miniz/$name.o" ]]; then
        arm-none-eabi-gcc -O2 -march=armv8-a+crc+crypto -mtune=cortex-a57 \
            -mfloat-abi=softfp -mfpu=neon-fp-armv8 -fPIE -DMINIZ_NO_ZLIB_COMPATIBLE_NAMES \
            -Iportlibs32/include/miniz -c "vendor/miniz/$name.c" -o "build/miniz/$name.o"
        changed=1
    fi
done
if [[ "$changed" == 1 || ! -f portlibs32/lib/libminiz.a ]]; then
    arm-none-eabi-ar rcs portlibs32/lib/libminiz.a build/miniz/*.o
fi

python runtime/tools/gen_imports.py --check
if ! make -j4 NX="$cache/libnx32/libnx32" > build/compile.log 2>&1; then
    tail -n 60 build/compile.log
    exit 1
fi
cp finn32.nsp finn32.build launcher/romfs/
if ! make -C launcher finn_nx.nacp > build/launcher.log 2>&1; then
    tail -n 60 build/launcher.log
    exit 1
fi
python tools/build_forwarder.py
if ! make -C launcher -j4 >> build/launcher.log 2>&1; then
    tail -n 60 build/launcher.log
    exit 1
fi
python tools/verify_build.py
