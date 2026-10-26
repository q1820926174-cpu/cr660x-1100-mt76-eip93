"""Apply the pinned OpenWrt package patch sets before the local compatibility edits."""
from pathlib import Path
import os
import subprocess

work = Path(os.environ['CR660X_WORK']) / 'mt76-noflash-20261026'
revision = (work / 'openwrt-revision.txt').read_text().strip()
assert revision == '4e1d1b7df0ce6fa96d7462dc883917682f428046'
ow = work / 'src' / ('openwrt-' + revision)
for directory, groups in [
    (work / 'src/backports-5.15.162-1', [ow / 'package/kernel/mac80211/patches/build', ow / 'package/kernel/mac80211/patches/subsys']),
    (work / 'src/mt76-2023-09-11-bdf8ea71', [ow / 'package/kernel/mt76/patches']),
]:
    marker = directory / '.matching-openwrt-patches'
    if marker.exists():
        continue
    for group in groups:
        for patch in sorted(group.glob('*.patch')):
            with patch.open('rb') as source:
                subprocess.run(['patch', '--batch', '--forward', '-p1', '-d', str(directory)], stdin=source, check=True)
    marker.write_text(revision + '\n')
