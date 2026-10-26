#!/bin/bash
set -euo pipefail
base=${CR660X_WORK:?set CR660X_WORK}
work=$base/hardware-baseline-20261026
source=$base/eip93/mtk-eip93-ca08387bf8352652129019bb19e2423ab313d5cb/crypto/mtk-eip93
tc=$base/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl
out=${CR660X_OUTPUT:?set CR660X_OUTPUT}/hardware-baseline-20261026/optional-eip93
export STAGING_DIR=$base/sdk/staging_dir
export PATH="$tc/bin:/usr/bin:/bin"
export KCFLAGS='-fno-caller-saves'
mkdir -p "$work/eip93" "$out"
cp "$source/"*.c "$source/"*.h "$source/Makefile" "$work/eip93/"
flags='-DCONFIG_CRYPTO_DEV_EIP93_SKCIPHER=1 -DCONFIG_CRYPTO_DEV_EIP93_AES=1 -DCONFIG_MTK_EIP93_GENERIC_SW_MAX_LEN=256 -DCONFIG_MTK_EIP93_AES_128_SW_MAX_LEN=256'
make -C "$work/kernel" ARCH=mips CROSS_COMPILE="$tc/bin/mipsel-openwrt-linux-musl-" M="$work/eip93" CONFIG_CRYPTO_DEV_EIP93=m CONFIG_CRYPTO_DEV_EIP93_SKCIPHER=y CONFIG_CRYPTO_DEV_EIP93_AEAD=n EXTRA_CFLAGS="$flags" -j2 modules > "$work/eip93-build.log" 2>&1
mkdir -p "$work/cbc"
cp "$work/kernel/crypto/cbc.c" "$work/cbc/"
printf 'obj-m += cbc.o\n' > "$work/cbc/Makefile"
make -C "$work/kernel" ARCH=mips CROSS_COMPILE="$tc/bin/mipsel-openwrt-linux-musl-" M="$work/cbc" modules > "$work/cbc-build.log" 2>&1
cp "$work/eip93/crypto-hw-eip93.ko" "$work/cbc/cbc.ko" "$out/"
"$tc/bin/mipsel-openwrt-linux-musl-strip" --strip-debug "$out/"*.ko
"$tc/bin/mipsel-openwrt-linux-musl-readelf" -p .modinfo "$out/crypto-hw-eip93.ko" > "$out/module-info.txt"
cp "$work/eip93-build.log" "$out/build.log"
sha256sum "$out/"*.ko > "$out/SHA256SUMS"
printf 'Optional AES-only EIP93 rebuilt against clean baseline, not installed or loaded.\n'
