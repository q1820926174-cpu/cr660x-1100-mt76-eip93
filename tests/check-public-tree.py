"""Source-only publication guard. Never prints matching secret contents."""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
allowed_top = {'.gitignore', '.gitattributes', 'README.md', 'BUILD.md', 'FIRMWARE.md', 'LICENSE',
               'NOTICE', 'sources.lock.json', 'SHA256SUMS', 'PUBLICATION-AUDIT.json',
               'build', 'config', 'overlay', 'public-overlay', 'patches', 'reference', 'tests', 'tools'}
blocked_suffix = {'.bin', '.uimage', '.ko', '.dtb', '.gz', '.xz', '.zip', '.7z', '.log', '.key', '.pem'}
patterns = [
    ('private-key', re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----')),
    ('credential-url', re.compile(r'(?:vless|vmess|trojan|ss)://', re.I)),
    ('github-token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b')),
    ('password-hash', re.compile(r'\$(?:1|5|6|y)\$[^\s:]+\$[^\s:]+')),
    ('host-path', re.compile(r'(?:[A-Z]:[\\/]Users[\\/]|\x2fmnt/[a-z]/Users/|\x2fhome/routerbuild/|WIN-[A-Z0-9]{8,})')),
    ('device-address', re.compile(r'(?<![0-9a-fA-F])(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}(?![0-9a-fA-F])')),
]
errors = []
count = 0
for path in sorted(root.rglob('*')):
    relative = path.relative_to(root)
    if relative.parts[0] == '.git' or '__pycache__' in relative.parts:
        continue
    if relative.parts[0] not in allowed_top:
        errors.append((str(relative), 'unexpected-public-path'))
        continue
    if path.is_symlink():
        errors.append((str(relative), 'symlink-not-reviewed'))
        continue
    if not path.is_file():
        continue
    count += 1
    if path.suffix.lower() in blocked_suffix:
        errors.append((str(relative), 'binary-or-private-artifact'))
        continue
    data = path.read_bytes()
    if b'\x00' in data:
        errors.append((str(relative), 'non-text-content'))
        continue
    text = data.decode('utf-8')
    for category, pattern in patterns:
        if pattern.search(text):
            errors.append((str(relative), category))
if errors:
    for path, category in errors:
        print(f'FAIL {category}: {path}')
    sys.exit(1)
print(f'PASS: {count} reviewed text files; no binary images or detected credential patterns')
