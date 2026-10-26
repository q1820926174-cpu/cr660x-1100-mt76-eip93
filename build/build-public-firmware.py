"""Build a complete PB-Boot image from a hash-pinned public base, never a device backup."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

BASE_SHA256 = 'e7d31ec39f0726f50524eb2a09b060143ec75aa2e492e1017c2ad3af3c91cecc'
KIT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-sysupgrade', type=Path, required=True)
    parser.add_argument('--components', type=Path, required=True,
                        help='Prepared source/SDK/native component workspace described in BUILD.md')
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True, help='New empty build directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--unsquashfs', default='unsquashfs', help='System squashfs-tools extractor')
    args = parser.parse_args()
    assert sha(args.base_sysupgrade) == BASE_SHA256, 'Input must be the pinned public upstream 5.4 image'
    assert not args.work.exists(), 'Use a new build directory; never reuse a device filesystem'
    args.work.mkdir(parents=True)
    root = args.work / 'rootfs'
    components = args.components.resolve()
    host = components / 'source/staging_dir/host/bin'
    native = components / 'mt76-noflash-20261026'
    baseline = components / 'hardware-baseline-20261026'
    tc = components / 'sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl/bin'
    readelf = tc / 'mipsel-openwrt-linux-musl-readelf'
    nm = tc / 'mipsel-openwrt-linux-musl-nm'

    with tarfile.open(args.base_sysupgrade) as archive:
        member = archive.getmember('sysupgrade-xiaomi_mi-router-cr660x/root')
        assert member.isfile()
        squashfs = args.work / 'upstream.squashfs'
        squashfs.write_bytes(archive.extractfile(member).read())
    run([args.unsquashfs, '-f', '-no-progress', '-processors', '2', '-d', root, squashfs])
    assert '5.10.252' in str(list((root/'lib/modules').iterdir()))

    def remove(relative):
        dest = root / relative
        assert root.resolve() in dest.parent.resolve().parents or dest.parent.resolve() == root.resolve()
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)

    def copy(source, relative, mode=0o644):
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            dest.unlink()
        shutil.copyfile(source, dest)
        dest.chmod(mode)

    def write(relative, content, mode=0o644):
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            dest.unlink()
        dest.write_text(content)
        dest.chmod(mode)

    # Remove obsolete vendor radio implementation and default password customization.
    for relative in ['lib/modules/5.10.252/mt_wifi.ko', 'etc/modules.d/mt7915',
        'lib/wifi', 'etc/wireless', 'usr/lib/lua/luci/controller/mtkwifi.lua',
        'usr/lib/lua/luci/view/mtkwifi', 'usr/lib/lua/luci/model/cbi/mtkwifi',
        'etc/uci-defaults/99-default-settings', 'etc/uci-defaults/50-root-passwd',
        'etc/uhttpd.key', 'etc/uhttpd.crt', 'etc/urandom.seed',
        'etc/dropbear/dropbear_rsa_host_key', 'etc/dropbear/dropbear_ed25519_host_key',
        'etc/dropbear/dropbear_ecdsa_host_key', 'etc/dropbear/authorized_keys', 'root/.ssh']:
        remove(relative)

    for subtree in ['overlay', 'public-overlay']:
        for source in sorted((KIT/subtree).rglob('*')):
            if source.is_file():
                rel = source.relative_to(KIT/subtree).as_posix()
                mode = 0o755 if rel.startswith(('etc/init.d/', 'sbin/')) or rel.endswith('cr660x-mt76-prepare') else 0o644
                copy(source, rel, mode)
    (root/'etc/config/cr660x_native').chmod(0o600)
    for source in (native/'bundle/modules').glob('*.ko'):
        copy(source, 'lib/modules/5.10.252/'+source.name)
    for source in (native/'bundle/firmware').rglob('*'):
        if source.is_file():
            copy(source, 'lib/firmware/'+source.relative_to(native/'bundle/firmware').as_posix())
    for name in ['iw','hostapd']:
        copy(native/'bundle/bin'/name, 'usr/sbin/'+name, 0o755)
    copy(components/'wifi-alternative/userspace/hostapd_cli', 'usr/sbin/hostapd_cli', 0o755)
    copy(baseline/'eip93/crypto-hw-eip93.ko', 'lib/modules/5.10.252/crypto-hw-eip93.ko')
    copy(baseline/'cbc/cbc.ko', 'lib/modules/5.10.252/cbc.ko')
    copy(components/'eip93/test-eip93-aes', 'usr/libexec/eip93-aes-selftest', 0o755)
    for name, text in {
        '09-crypto-cbc': 'cbc\n', '10-crypto-hw-eip93-aes': 'crypto-hw-eip93\n',
        '20-cmac':'cmac\n', '25-mt76-native':'compat\ncfg80211\nmac80211\nmt76\nmt76-connac-lib\nmt7915e\n',
    }.items():
        write('etc/modules.d/'+name, text)
    for name, target in [('S16eip93-selftest','eip93-selftest'),('S25cr660x-mt76','cr660x-mt76'),('K89cr660x-mt76','cr660x-mt76')]:
        (root/'etc/rc.d'/name).symlink_to('../init.d/'+target)

    # Public OpenWrt-style first login: no preloaded root password or device keys.
    shadow = (root/'etc/shadow').read_text()
    assert re.search(r'^root:', shadow, flags=re.M)
    write('etc/shadow', re.sub(r'^root:[^:]*:', 'root::', shadow, flags=re.M), 0o600)
    write('etc/uci-defaults/99-cr660x-public', '''#!/bin/sh
uci -q set system.@system[0].hostname='CR660X'
uci -q set system.@system[0].timezone='CST-8'
uci -q set system.@system[0].zonename='Asia/Shanghai'
uci commit system
exit 0
''', 0o755)
    write('etc/cr660x-public-release', 'CR660x 1100MHz native mt7915e AES experimental public image\n2.4GHz association unresolved; not cold-boot tested\n')

    # Register the newly supplied components and remove the deleted vendor package records.
    status_path = root/'usr/lib/opkg/status'
    blocks = status_path.read_text().split('\n\n')
    removed = []
    kept = []
    native_names = {'kmod-crypto-cbc','kmod-crypto-cmac','kmod-cfg80211','kmod-mac80211',
                    'kmod-mt76-core','kmod-mt76-connac','kmod-mt7915e','kmod-crypto-hw-eip93-aes-lab'}
    for block in blocks:
        match = re.search(r'^Package: (.+)$', block, re.M)
        if match and (match[1] in native_names or match[1] in {'kmod-mt7915','kmod-mt7915d','luci-app-mtkwifi'}):
            removed.append(match[1])
        elif block.strip():
            kept.append(block)
    packages = [
        ('kmod-crypto-cbc', ['cbc.ko']), ('kmod-crypto-cmac',['cmac.ko']),
        ('kmod-crypto-hw-eip93-aes-lab',['crypto-hw-eip93.ko']),
        ('kmod-cfg80211',['compat.ko','cfg80211.ko']), ('kmod-mac80211',['mac80211.ko']),
        ('kmod-mt76-core',['mt76.ko']), ('kmod-mt76-connac',['mt76-connac-lib.ko']),
        ('kmod-mt7915e',['mt7915e.ko'])]
    for name, modules in packages:
        kept.append(f'Package: {name}\nVersion: 5.10.252+cr660x-public1\nDepends: kernel\nStatus: install user installed\nArchitecture: mipsel_24kc\nDescription: Matching experimental native component')
        write('usr/lib/opkg/info/'+name+'.list', ''.join('/lib/modules/5.10.252/'+m+'\n' for m in modules))
    status_path.write_text('\n\n'.join(kept)+'\n\n')
    for name in removed:
        if name not in native_names:
            for path in (root/'usr/lib/opkg/info').glob(name+'.*'):
                path.unlink()

    exports = {line.split()[1] for line in (baseline/'kernel/Module.symvers').read_text().splitlines()}
    modules = list((root/'lib/modules/5.10.252').glob('*.ko'))
    # All module exports, not just the new radio modules, must be available.
    for module in modules:
        symbols = subprocess.check_output([str(nm), str(module)], text=True)
        exports.update(line.split()[-1][len('__ksymtab_'):] for line in symbols.splitlines()
                       if len(line.split())>=3 and line.split()[-1].startswith('__ksymtab_'))
    for module in modules:
        info = subprocess.check_output([str(readelf), '-p', '.modinfo', str(module)], text=True)
        assert 'vermagic=5.10.252 SMP mod_unload MIPS32_R2 32BIT' in info, module.name
        symbols = subprocess.check_output([str(nm), '-u', str(module)], text=True)
        required = {line.split()[-1] for line in symbols.splitlines() if len(line.split())==2 and line.split()[0]=='U'}
        assert not required-exports, (module.name, sorted(required-exports))

    # Run the actual target Lua against this rootfs. QEMU does not emulate radio hardware.
    generated = args.work/'hostapd-check'
    generated.mkdir(mode=0o700)
    env = os.environ.copy()
    env.update({'LUA_PATH':str(root/'usr/lib/lua/?.lua')+';;', 'LUA_CPATH':str(root/'usr/lib/lua/?.so')+';;'})
    run(['qemu-mipsel','-L',root,root/'usr/bin/lua',root/'usr/libexec/cr660x-mt76-config.lua',root,generated],env=env)
    for band in [0,1]:
        values = dict(line.split('=',1) for line in (generated/f'hostapd-{band}.conf').read_text().splitlines() if '=' in line)
        assert values['ssid'] == ('CR660X_2G' if band==0 else 'CR660X_5G')
        assert values['wpa_passphrase'] == 'cr660x-setup'
    for source in list((root/'etc/init.d').glob('cr660x*'))+[root/'sbin/wifi',root/'etc/init.d/eip93-selftest',root/'usr/libexec/cr660x-mt76-prepare']:
        run(['sh','-n',source])

    squashfs = args.work/'rootfs.squashfs'
    run([host/'mksquashfs4',root,squashfs,'-noappend','-nopad','-all-root','-comp','xz','-b','262144','-processors','2'])
    env = os.environ.copy()
    env.update({'TOPDIR':str(components/'source'), 'PATH':str(host)+':/usr/bin:/bin'})
    ubi = args.work/'rootfs.ubi'
    run(['sh',components/'source/scripts/ubinize-image.sh','--rootfs',squashfs,ubi,'-p','128KiB','-m','2048','-E','5'],env=env)
    run(['python3',KIT/'tools/pack-pbboot.py','--kernel',args.kernel,'--ubi',ubi,'--output',args.output])
    report = {
        'status':'FULL_IMAGE_OFFLINE_CHECKED_NOT_FLASHED_NOT_BOOT_QUALIFIED',
        'public_base_sha256':BASE_SHA256, 'kernel_sha256':sha(args.kernel),
        'image_sha256':sha(args.output), 'image_bytes':args.output.stat().st_size,
        'rootfs_input':'pinned original author public 5.4 squashfs, not a personal filesystem',
        'default_lan':'192.168.50.1', 'wan':'DHCP on physical WAN port',
        'default_root_password':'empty; set at first login',
        'public_setup_wifi_key':'cr660x-setup',
        'included':['LuCI web management','DHCP/DNS/firewall','WAN DHCP and PPPoE support','native Wi-Fi settings page','1100MHz kernel','mt7915e','EIP-93 AES'],
        'excluded':['personal configurations','proxy subscriptions/nodes','device Factory/EEPROM/NVRAM/Bdata','vendor mt_wifi module'],
        'module_count_checked':len(modules), 'known_issues':['2.4GHz association unresolved','fresh image has not booted on hardware','AES production CPU/throughput benefit unproven'],
    }
    args.output.with_suffix('.verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
