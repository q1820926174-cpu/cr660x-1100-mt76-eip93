"""Download only the identified public upstream base and verify its fixed SHA256."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Refuse to overwrite an existing input'
uri = 'cloudreve://o9GTK@share/5.4/openwrt-ramips-mt7621-xiaomi_mi-router-cr660x-squashfs-sysupgrade.bin'
request = urllib.request.Request('https://yun.heleguo.cn/api/v4/file/url',
    data=json.dumps({'uris':[uri]}).encode(), headers={'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)
assert result.get('code') == 0, 'Public upstream download service returned an error'
url = result['data']['urls'][0]['url']
with urllib.request.urlopen(url, timeout=120) as response:
    data = response.read(32*1024*1024+1)
assert len(data) == 11838594, 'Unexpected upstream archive length'
assert hashlib.sha256(data).hexdigest() == 'e7d31ec39f0726f50524eb2a09b060143ec75aa2e492e1017c2ad3af3c91cecc', 'Upstream checksum changed; do not substitute another build'
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('xb') as output:
    output.write(data)
print('Pinned public upstream 5.4 image downloaded and verified')
