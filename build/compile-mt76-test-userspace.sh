#!/bin/bash
set -euo pipefail
base=${CR660X_WORK:?set CR660X_WORK}
work="$base/wifi-alternative"
tc="$base/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl"
export STAGING_DIR="$base/sdk/staging_dir"
export PATH="$tc/bin:/usr/bin:/bin:$base/sdk/staging_dir/host/bin"
nl="$work/src/libnl-tiny"
hap="$work/src/hostapd-2023-06-22-599d00be/hostapd"
cmake -S "$nl" -B "$work/libnl-build" -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_C_COMPILER="$tc/bin/mipsel-openwrt-linux-musl-gcc" -DCMAKE_AR="$tc/bin/mipsel-openwrt-linux-musl-ar" -DCMAKE_RANLIB="$tc/bin/mipsel-openwrt-linux-musl-ranlib" -DCMAKE_BUILD_TYPE=Release >"$work/libnl-config.log" 2>&1
cmake --build "$work/libnl-build" --target nl-tiny-static -j2 >"$work/libnl-build.log" 2>&1
cat >"$hap/.config" <<EOF
CONFIG_DRIVER_NL80211=y
CONFIG_LIBNL_TINY=y
CONFIG_IEEE80211N=y
CONFIG_IEEE80211AC=y
CONFIG_IEEE80211AX=y
CONFIG_TLS=internal
CONFIG_CRYPTO=internal
CONFIG_INTERNAL_LIBTOMMATH=y
CONFIG_NO_ACCOUNTING=y
CONFIG_NO_RADIUS=y
CONFIG_NO_VLAN=y
CFLAGS += -O2 -march=mips32r2 -msoft-float -D_GNU_SOURCE -I$nl/include
LDFLAGS += -static -L$work/libnl-build
EOF
nice -n 10 make -C "$hap" CC="$tc/bin/mipsel-openwrt-linux-musl-gcc" -j2 hostapd hostapd_cli >"$work/hostapd-build.log" 2>&1
cd "$work/downloads"
curl --fail --location --retry 2 --max-time 120 -o iw-6.9.tar.xz https://sources.openwrt.org/iw-6.9.tar.xz
echo '3f2db22ad41c675242b98ae3942dbf3112548c60a42ff739210f2de4e98e4894  iw-6.9.tar.xz' | sha256sum -c -
tar -xJf iw-6.9.tar.xz -C "$work/src"
iw="$work/src/iw-6.9"
if [ ! -f "$iw/.openwrt-patches-applied" ]; then
  for p in "$base/source/package/network/utils/iw/patches/"*.patch; do
    patch --batch --forward -p1 -d "$iw" < "$p" >>"$work/iw-patches.log" 2>&1
  done
  touch "$iw/.openwrt-patches-applied"
fi
echo 'const char iw_version[] = "6.9-mt76-lab";' >"$iw/version.c"
nice -n 10 make -C "$iw" CC="$tc/bin/mipsel-openwrt-linux-musl-gcc" CFLAGS="-O2 -march=mips32r2 -msoft-float -I$nl/include -DCONFIG_LIBNL20 -D_GNU_SOURCE -DIW_FULL" LDFLAGS="-static -L$work/libnl-build" NL1FOUND= NL2FOUND=Y NLLIBNAME=libnl-tiny LIBS='-lm -lnl-tiny' IW_FULL=1 -j2 >"$work/iw-build.log" 2>&1
mkdir -p "$work/userspace"
cp "$hap/hostapd" "$hap/hostapd_cli" "$iw/iw" "$work/userspace/"
"$tc/bin/mipsel-openwrt-linux-musl-strip" "$work/userspace/"*
printf 'Static userspace tools built. No router changes.\n'
