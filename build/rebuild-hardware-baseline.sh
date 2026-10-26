#!/bin/bash
set -euo pipefail
base=${CR660X_WORK:?set CR660X_WORK}
src=$base/source
original=$src/build_dir/target-mipsel-openwrt-linux-musl_musl/linux-ramips_mt7621/linux-5.10.252
work=$base/hardware-baseline-20261026
analysis=${CR660X_OUTPUT:?set CR660X_OUTPUT}
tc=$base/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl
export STAGING_DIR=$base/sdk/staging_dir
export PATH="$tc/bin:/usr/bin:/bin:$src/staging_dir/host/bin"
export KCFLAGS='-fno-caller-saves'
export KBUILD_BUILD_USER=routerbuild
export KBUILD_BUILD_HOST=buildhost
export KBUILD_BUILD_VERSION=0
export KBUILD_BUILD_TIMESTAMP='Sat May 9 09:59:15 2026'
mkdir -p "$work" "$analysis/hardware-baseline-20261026"
if [ ! -e "$work/kernel" ]; then cp -a --reflink=auto "$original" "$work/kernel"; fi
cp "$original/.config" "$work/approved.config"
make -C "$work/kernel" ARCH=mips CROSS_COMPILE="mipsel-openwrt-linux-musl-" clean > "$work/clean.log" 2>&1
cp "$work/approved.config" "$work/kernel/.config"
make -C "$work/kernel" ARCH=mips CROSS_COMPILE="mipsel-openwrt-linux-musl-" olddefconfig > "$work/config.log" 2>&1
"$work/kernel/scripts/diffconfig" "$work/approved.config" "$work/kernel/.config" > "$work/config-delta.txt"
test ! -s "$work/config-delta.txt"
nice -n 10 make -C "$work/kernel" ARCH=mips CROSS_COMPILE="mipsel-openwrt-linux-musl-" -j4 vmlinux modules > "$work/build.log" 2>&1
"$tc/bin/mipsel-openwrt-linux-musl-objcopy" -O binary -R .reginfo -R .notes -R .note -R .comment -R .mdebug -R .note.gnu.build-id -S "$work/kernel/vmlinux" "$work/kernel.raw"
test -f "$CR660X_DTB"
cat "$work/kernel.raw" "$CR660X_DTB" > "$work/kernel-with-dtb.raw"
"$src/staging_dir/host/bin/lzma" e "$work/kernel-with-dtb.raw" -lc1 -lp2 -pb2 "$work/kernel.lzma"
make -C "$src/target/linux/ramips/image/lzma-loader" TOPDIR="$src" KDIR="$work" PKG_BUILD_DIR="$work/loader-build" TARGET_DIR="$work" LOADER_NAME=loader PLATFORM=mt7621 LZMA_TEXT_START=0x80a00000 LOADADDR=0x80001000 LOADER_DATA="$work/kernel.lzma" compile loader.bin > "$work/loader.log" 2>&1
SOURCE_DATE_EPOCH=1778320755 "$src/staging_dir/host/bin/mkimage" -A mips -O linux -T kernel -C none -a 0x80001000 -e 0x80001000 -n 'CR660x 1100 baseline rebuild' -d "$work/loader.bin" "$work/kernel.uimage"
cp "$work/kernel.uimage" "$analysis/hardware-baseline-20261026/cr660x-1100-clean-rebuild-UNTESTED.uimage"
cp "$work/kernel/.config" "$work/kernel/Module.symvers" "$work/config-delta.txt" "$analysis/hardware-baseline-20261026/"
printf 'CLEAN_BUILD_COMPLETE_LOCAL_ONLY\n'
