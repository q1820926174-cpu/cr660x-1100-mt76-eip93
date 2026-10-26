#!/bin/bash
set -euo pipefail
work=${CR660X_WORK:?set CR660X_WORK}/mt76-noflash-20261026
mkdir -p "$work/downloads" "$work/src"
cd "$work/downloads"
curl -fL --max-time 120 -o backports-5.15.162-1.tar.xz https://sources.openwrt.org/backports-5.15.162-1.tar.xz
echo '00444ab103f5e4ce34d3ba7895289d2b78b84f14a35f9021b60cb1a0270dfec5  backports-5.15.162-1.tar.xz' | sha256sum -c -
curl -fL --max-time 120 -o mt76-2023-09-11-bdf8ea71.tar.xz https://sources.openwrt.org/mt76-2023-09-11-bdf8ea71.tar.xz
echo 'a080a83068abc204d1f563022391625875ef77deda14be49888c179ff78fa8c8  mt76-2023-09-11-bdf8ea71.tar.xz' | sha256sum -c -
revision=4e1d1b7df0ce6fa96d7462dc883917682f428046
test ${#revision} -eq 40
printf '%s\n' "$revision" > "$work/openwrt-revision.txt"
curl -fL --max-time 120 -o openwrt-22.03.tar.gz "https://codeload.github.com/openwrt/openwrt/tar.gz/$revision"
sha256sum openwrt-22.03.tar.gz > "$work/openwrt-archive.sha256"
tar -xJf backports-5.15.162-1.tar.xz -C "$work/src"
tar -xJf mt76-2023-09-11-bdf8ea71.tar.xz -C "$work/src"
tar -xzf openwrt-22.03.tar.gz -C "$work/src" "openwrt-$revision/package/kernel/mac80211" "openwrt-$revision/package/kernel/mt76"
echo SOURCES_VERIFIED_AND_EXTRACTED
