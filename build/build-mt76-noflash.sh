#!/bin/bash
set -euo pipefail
base=${CR660X_WORK:?set CR660X_WORK}
work=$base/mt76-noflash-20261026
bp=$work/src/backports-5.15.162-1
mt=$work/src/mt76-2023-09-11-bdf8ea71
kdir=$base/hardware-baseline-20261026/kernel
revision=$(cat "$work/openwrt-revision.txt")
ow=$work/src/openwrt-$revision
tc=$base/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl
export STAGING_DIR=$base/sdk/staging_dir
export PATH="$tc/bin:/usr/bin:/bin:$base/source/staging_dir/host/bin"
export KCFLAGS=-fno-caller-saves
if [ ! -f "$bp/.matching-openwrt-patches" ]; then
  for group in build subsys; do
    for p in "$ow/package/kernel/mac80211/patches/$group/"*.patch; do
      test -f "$p" || continue
      patch --batch --forward -p1 -d "$bp" < "$p" >> "$work/patches.log" 2>&1
    done
  done
  touch "$bp/.matching-openwrt-patches"
fi
if [ ! -f "$mt/.matching-openwrt-patches" ]; then
  for p in "$ow/package/kernel/mt76/patches/"*.patch; do
    test -f "$p" || continue
    patch --batch --forward -p1 -d "$mt" < "$p" >> "$work/patches.log" 2>&1
  done
  touch "$mt/.matching-openwrt-patches"
fi
cat > "$bp/.config" <<'EOF'
CPTCFG_CFG80211=m
CPTCFG_MAC80211=m
CPTCFG_CFG80211_CERTIFICATION_ONUS=y
CPTCFG_MAC80211_RC_MINSTREL=y
CPTCFG_MAC80211_RC_MINSTREL_HT=y
CPTCFG_MAC80211_RC_MINSTREL_VHT=y
CPTCFG_MAC80211_RC_DEFAULT_MINSTREL=y
CPTCFG_WLAN=y
EOF
make -C "$bp" ARCH=mips CROSS_COMPILE=mipsel-openwrt-linux-musl- KLIB_BUILD="$kdir" KLIB="$work/modules" allnoconfig > "$work/backports-config.log" 2>&1
nice -n 10 make -C "$bp" ARCH=mips CROSS_COMPILE=mipsel-openwrt-linux-musl- KLIB_BUILD="$kdir" KLIB="$work/modules" -j4 modules > "$work/backports-build.log" 2>&1
echo BACKPORTS_COMPLETE
flags="-I$mt -I$bp/backport-include -I$bp/backport-include/uapi -I$bp/include -I$bp/include/uapi -include $bp/backport-include/backport/autoconf.h -include $bp/backport-include/backport/backport.h"
nice -n 10 make -C "$kdir" ARCH=mips CROSS_COMPILE=mipsel-openwrt-linux-musl- M="$mt" KBUILD_EXTRA_SYMBOLS="$bp/Module.symvers" NOSTDINC_FLAGS="$flags" CONFIG_MT76_CORE=m CONFIG_MT76_CONNAC_LIB=m CONFIG_MT7915E=m -j4 modules > "$work/mt76-build.log" 2>&1
mkdir -p "$work/cmac"
cp "$kdir/crypto/cmac.c" "$work/cmac/"
printf 'obj-m += cmac.o\n' > "$work/cmac/Makefile"
make -C "$kdir" ARCH=mips CROSS_COMPILE=mipsel-openwrt-linux-musl- M="$work/cmac" modules > "$work/cmac-build.log" 2>&1
echo MT76_AND_CMAC_COMPLETE_NO_KERNEL_CHANGES
