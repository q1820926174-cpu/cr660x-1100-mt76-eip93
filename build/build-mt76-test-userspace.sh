#!/bin/bash
set -euo pipefail
base=${CR660X_WORK:?set CR660X_WORK}
work="$base/wifi-alternative"
tc="$base/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl"
export STAGING_DIR="$base/sdk/staging_dir"
export PATH="$tc/bin:/usr/bin:/bin"
cd "$work/downloads"
curl --fail --location --retry 2 --max-time 120 -o hostapd-2023-06-22-599d00be.tar.xz https://sources.openwrt.org/hostapd-2023-06-22-599d00be.tar.xz
echo '828810c558ea181e45ed0c8b940f5c41e55775e2979a15aed8cf0ab17dd7723c  hostapd-2023-06-22-599d00be.tar.xz' | sha256sum -c -
tar -xJf hostapd-2023-06-22-599d00be.tar.xz -C "$work/src"
if [ ! -d "$work/src/libnl-tiny/.git" ]; then
  git init "$work/src/libnl-tiny"
  git -C "$work/src/libnl-tiny" remote add origin https://github.com/openwrt/libnl-tiny.git
  git -C "$work/src/libnl-tiny" fetch --depth=1 origin 40493a655d8caa2ccf5206dde1e733abe2920432
  git -C "$work/src/libnl-tiny" checkout --detach FETCH_HEAD
fi
test "$(git -C "$work/src/libnl-tiny" rev-parse HEAD)" = 40493a655d8caa2ccf5206dde1e733abe2920432
printf 'Userspace sources verified and extracted.\n'
