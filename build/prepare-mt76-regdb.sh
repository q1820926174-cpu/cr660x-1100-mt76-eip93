#!/bin/bash
set -euo pipefail
work=${CR660X_WORK:?set CR660X_WORK}/wifi-alternative
mkdir -p "$work/bundle/firmware"
cd "$work/downloads"
curl --fail --location --retry 2 --max-time 120 -o wireless-regdb-2026.09.03.tar.xz https://sources.openwrt.org/wireless-regdb-2026.09.03.tar.xz
echo 'b22e0901227b820cd1c280abe681a15b773a5103a5e10dc442e94ebb34cbf58d  wireless-regdb-2026.09.03.tar.xz' | sha256sum -c -
tar -xJf wireless-regdb-2026.09.03.tar.xz -C "$work/src"
python3 "$work/src/wireless-regdb-2026.09.03/db2fw.py" "$work/bundle/firmware/regulatory.db" "$work/src/wireless-regdb-2026.09.03/db.txt"
printf 'Regulatory DB staged from verified current upstream source.\n'
