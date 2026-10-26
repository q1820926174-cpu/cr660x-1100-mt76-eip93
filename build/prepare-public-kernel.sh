#!/bin/bash
set -euo pipefail
base=${CR660X_WORK:?set CR660X_WORK}
out=${CR660X_OUTPUT:?set CR660X_OUTPUT}
src=$base/source
kdir=$base/hardware-baseline-20261026/kernel
tc=$base/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl/bin
export PATH="$tc:$src/staging_dir/host/bin:/usr/bin:/bin"
export STAGING_DIR="$base/sdk/staging_dir"
mkdir -p "$out"
test -f "$kdir/vmlinux"
export KCFLAGS=-fno-caller-saves
export KBUILD_BUILD_USER=builder
export KBUILD_BUILD_HOST=buildhost
export KBUILD_BUILD_VERSION=0
export KBUILD_BUILD_TIMESTAMP='Sat May 9 09:59:15 2026'
make -C "$kdir" ARCH=mips CROSS_COMPILE=mipsel-openwrt-linux-musl- -j"${JOBS:-4}" vmlinux > "$out/kernel-version-build.log" 2>&1
dtc="$kdir/scripts/dtc/dtc"
test -x "$dtc"
mipsel-openwrt-linux-musl-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I "$kdir/include" -I "$src/target/linux/ramips/dts" \
  "$src/target/linux/ramips/dts/mt7621_xiaomi_mi-router-cr660x.dts" > "$out/cr660x.dts.preprocessed"
"$dtc" -I dts -O dtb -o "$out/cr660x.dtb" "$out/cr660x.dts.preprocessed"
mipsel-openwrt-linux-musl-objcopy -O binary -R .reginfo -R .notes -R .note \
  -R .comment -R .mdebug -R .note.gnu.build-id -S "$kdir/vmlinux" "$out/kernel.raw"
cat "$out/kernel.raw" "$out/cr660x.dtb" > "$out/kernel-with-dtb.raw"
"$src/staging_dir/host/bin/lzma" e "$out/kernel-with-dtb.raw" -lc1 -lp2 -pb2 "$out/kernel.lzma"
make -C "$src/target/linux/ramips/image/lzma-loader" TOPDIR="$src" KDIR="$out" \
  PKG_BUILD_DIR="$out/loader-build" TARGET_DIR="$out" LOADER_NAME=loader \
  PLATFORM=mt7621 LZMA_TEXT_START=0x80a00000 LOADADDR=0x80001000 \
  LOADER_DATA="$out/kernel.lzma" compile loader.bin
SOURCE_DATE_EPOCH=1778320755 "$src/staging_dir/host/bin/mkimage" \
  -A mips -O linux -T kernel -C none -a 0x80001000 -e 0x80001000 \
  -n 'CR660x 1100 public experimental' -d "$out/loader.bin" "$out/kernel.uimage"
