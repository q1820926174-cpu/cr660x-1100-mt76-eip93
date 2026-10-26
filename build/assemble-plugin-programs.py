"""Export installed package PROGRAM files into a clean, reviewable component bundle.

Never exports live configuration, service credentials, custom rule lists or runtime data.
The resulting bundle requires a separate unpacked-file and sensitive-value review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile

PASSWALL_SOURCE_SHA = '2e161036b754411a51be5e66dad8d149e1ab613e7207b528da027b092a261ad5'
PASSWALL_COMMIT = '32ac46d42911453da27ced0247e70156016e0a4f'

def packages(root):
    result = {}
    for block in (root/'usr/lib/opkg/status').read_text().split('\n\n'):
        fields = dict(re.findall(r'^([A-Za-z-]+): (.*)$', block, re.M))
        if 'Package' in fields and fields.get('Status','').split()[-1:] == ['installed']:
            result[fields['Package']] = fields
    return result

def sha(data):
    return hashlib.sha256(data).hexdigest()

def allowed(relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and '..' not in path.parts
    if path.suffix.lower() in {'.key','.pem','.crt','.log','.db','.sqlite','.dat','.bak'}:
        return False
    if relative.startswith(('usr/share/passwall/rules/', 'usr/share/xray/', 'usr/share/v2ray/')):
        return False
    if relative == 'usr/share/passwall/0_default_config':
        return False
    return relative.startswith(('usr/bin/','usr/sbin/','usr/lib/','usr/share/','www/luci-static/','lib/','etc/init.d/','etc/hotplug.d/'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-root', type=Path, required=True)
    parser.add_argument('--clean-base', type=Path, required=True)
    parser.add_argument('--passwall-source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.work.exists() and not args.output.exists()
    assert sha(args.passwall_source.read_bytes()) == PASSWALL_SOURCE_SHA
    old, base = packages(args.installed_root), packages(args.clean_base)
    selected = {name:fields for name,fields in old.items() if name not in base and name not in {'kmod-mt7915','luci-app-mtk','wifi-profile'}}
    assert {'luci-app-passwall','xray-core','ddnsto','luci-app-ddnsto','vlmcsd','luci-app-vlmcsd'} <= selected.keys()
    root = args.work/'rootfs'
    root.mkdir(parents=True)
    excluded = []
    missing = []
    owners = {}

    def copy(source, relative, owner):
        dest = root/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink() or dest.is_file(): dest.unlink()
        mode = source.lstat().st_mode
        if stat.S_ISLNK(mode):
            dest.symlink_to(os.readlink(source))
        elif stat.S_ISREG(mode):
            shutil.copyfile(source,dest)
            dest.chmod(0o755 if mode & 0o111 else 0o644)
        else:
            raise ValueError('Unexpected package file type: '+relative)
        owners[relative]=owner

    for name, fields in sorted(selected.items()):
        info = args.installed_root/'usr/lib/opkg/info'
        filelist = info/(name+'.list')
        assert filelist.is_file(), 'Missing installed file manifest: '+name
        conf = info/(name+'.conffiles')
        conffiles = {line.split()[0].lstrip('/') for line in conf.read_text().splitlines() if line.strip()} if conf.exists() else set()
        for line in filelist.read_text().splitlines():
            relative = line.lstrip('/')
            if not allowed(relative) or relative in conffiles:
                excluded.append(relative)
                continue
            source = args.installed_root/relative
            if source.is_symlink():
                copy(source,relative,name)
            elif source.is_file():
                copy(source,relative,name)
            elif source.is_dir():
                continue
            else:
                missing.append(relative)

    # Rebuild the Passwall application from its matching public source, including
    # defaults and rules; never reuse a user's editable rules or node template.
    with tarfile.open(args.passwall_source) as archive:
        prefix = 'openwrt-passwall-'+PASSWALL_COMMIT+'/luci-app-passwall/'
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith(prefix): continue
            relative = member.name[len(prefix):]
            if relative.startswith('root/'):
                target = relative[len('root/'):]
            elif relative.startswith('luasrc/'):
                target = 'usr/lib/lua/luci/'+relative[len('luasrc/'):]
            elif relative.startswith('htdocs/'):
                target = 'www/'+relative[len('htdocs/'):]
            else:
                continue
            assert '..' not in PurePosixPath(target).parts
            dest = root/target;dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.is_symlink(): dest.unlink()
            dest.write_bytes(archive.extractfile(member).read())
            dest.chmod(0o755 if member.mode & 0o111 else 0o644)
            owners[target]='luci-app-passwall'

    def write(relative,text,mode=0o644,owner='luci-app-passwall'):
        dest = root/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(text);dest.chmod(mode)
        owners[relative]=owner

    defaults = root/'usr/share/passwall/0_default_config'
    assert defaults.is_file()
    text = defaults.read_text()
    assert re.search(r"option enabled ['\"]0['\"]",text)
    assert not re.search(r'^config (?:node_subscribe|subscribe_list)\b',text,re.M)
    write('etc/config/passwall',text,0o600)
    write('etc/config/ddnsto',"config ddnsto 'ddnsto'\n\toption enabled '0'\n\toption token ''\n\toption index '0'\n\toption logger '0'\n\toption feat_enabled '0'\n",0o600,owner='ddnsto')
    write('etc/config/vlmcsd',"config vlmcsd 'config'\n\toption enabled '0'\n\toption auto_activate '0'\n\toption internet_access '0'\n",0o600,owner='vlmcsd')
    write('etc/vlmcsd.ini','; Clean public setup: no user-specific settings\n',owner='vlmcsd')
    write('etc/uci-defaults/98-public-plugin-users',"""#!/bin/sh
. /lib/functions.sh
if ! user_exists vlmcsd; then
    service_gid=$(group_add_next vlmcsd) || exit 1
    user_add vlmcsd '' "$service_gid" 'KMS service' /var/run/vlmcsd /bin/false || exit 1
fi
exit 0
""",0o755,owner='vlmcsd')
    # Services can start at boot after user configuration, but public defaults
    # leave proxy/remote-access/KMS service functionality disabled.
    for service in ['passwall','passwall_server','ddnsto','vlmcsd']:
        source = root/'etc/init.d'/service
        assert source.exists(),service
        start = re.search(r'^START=[\"\']?(\d+)',source.read_text(),re.M)
        assert start,service
        link=root/'etc/rc.d'/('S'+start[1]+service)
        link.parent.mkdir(parents=True,exist_ok=True)
        link.symlink_to('../init.d/'+service)
        owners[link.relative_to(root).as_posix()]='luci-app-passwall' if service.startswith('passwall') else service

    manifest = {
        'format':1,'passwall_public_source_commit':PASSWALL_COMMIT,
        'passwall_public_source_sha256':PASSWALL_SOURCE_SHA,
        'program_origin':'installed package file allowlist; Passwall source/defaults/rules rebuilt from matching public upstream',
        'configuration_origin':'public upstream defaults or explicit empty/disabled public templates',
        'packages':[{key:value for key,value in fields.items() if key in {'Package','Version','Depends','Provides','Architecture','License','Source','SourceName','URL','Description'}} for name,fields in sorted(selected.items())],
        'retained_clean_base_versions':[{key:base[name][key] for key in ['Package','Version']} for name in sorted(old.keys() & base.keys()) if old[name].get('Version')!=base[name].get('Version')],
        'excluded_classes':['original /etc/config','credentials','user-editable custom rules','runtime data','original host identities','obsolete mt_wifi driver'],
        'excluded_path_count':len(set(excluded)), 'files':[]}
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root).as_posix()
        mode=path.lstat().st_mode
        if stat.S_ISLNK(mode):
            record={'path':relative,'type':'symlink','target':os.readlink(path)}
        elif stat.S_ISREG(mode):
            record={'path':relative,'type':'file','sha256':sha(path.read_bytes()),'bytes':path.stat().st_size,'mode':stat.S_IMODE(mode)}
        elif stat.S_ISDIR(mode): continue
        else: raise ValueError(relative)
        record['package']=owners[relative]
        manifest['files'].append(record)
    (args.work/'plugins-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(args.output,'w:gz',format=tarfile.GNU_FORMAT) as archive:
        for path in [args.work/'plugins-manifest.json']+[root/item['path'] for item in manifest['files']]:
            name='plugins-manifest.json' if path.name=='plugins-manifest.json' and path.parent==args.work else 'rootfs/'+path.relative_to(root).as_posix()
            info=archive.gettarinfo(str(path),arcname=name)
            info.uid=info.gid=0;info.uname=info.gname='root';info.mtime=1778457600
            if info.isfile():
                with path.open('rb') as source:archive.addfile(info,source)
            else: archive.addfile(info)
    print(json.dumps({'packages':len(selected),'program_and_clean_default_files':len(manifest['files']),'bundle_sha256':sha(args.output.read_bytes()),'bundle_bytes':args.output.stat().st_size,'missing_package_files':missing},indent=2))

if __name__=='__main__':main()
