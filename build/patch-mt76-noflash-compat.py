from pathlib import Path
import os
import subprocess
work=Path(os.environ['CR660X_WORK']) / 'mt76-noflash-20261026'
bp=work/'src/backports-5.15.162-1'
mt=work/'src/mt76-2023-09-11-bdf8ea71'
marker=work/'.noflash-compat-applied'
assert not marker.exists()
changes=[]
def edit(p,transform):
    old=p.read_text(); new=transform(old)
    assert new!=old
    saved=work/(p.name+'.before-noflash')
    saved.write_text(old);p.write_text(new)
    diff=subprocess.run(['diff','-u',str(saved),str(p)],capture_output=True,text=True)
    changes.append(diff.stdout)
def nl(s):
    old='NL80211_MCGRP_REGULATORY, GFP_ATOMIC);'
    assert s.count(old)==2
    return s.replace(old,'NL80211_MCGRP_REGULATORY);')
edit(bp/'net/wireless/nl80211.c',nl)
def overflow(s):
    old='#define is_signed_type(type)       (((type)(-1)) < (type)1)'
    assert s.count(old)==1
    return s.replace(old,'#ifndef is_signed_type\n'+old+'\n#endif')
edit(bp/'include/linux/overflow.h',overflow)
def mac_config(s):
    old='\tdepends on CRYPTO_CMAC\n'
    assert s.count(old)==1
    return s.replace(old,'\t# CMAC is supplied as a matching external runtime module for this trial.\n')
edit(bp/'net/mac80211/Kconfig',mac_config)
def debug(s):
    begin=s.index('static struct dentry *\ncreate_buf_file_cb')
    end=s.index('\nstatic int\nmt7915_fw_debug_bin_get',begin)
    block=s[begin:end]
    replacement='#if IS_ENABLED(CONFIG_RELAY)\n'+block+'\n#else\nstatic int\nmt7915_fw_debug_bin_set(void *data, u64 val)\n{\n\treturn -EOPNOTSUPP;\n}\n#endif\n'
    s=s[:begin]+replacement+s[end:]
    begin=s.index('static void\nmt7915_debugfs_write_fwlog')
    body=s.index('{',begin)+1
    end=s.index('\n}\n\nvoid mt7915_debugfs_rx_fw_monitor',body)
    s=s[:body]+'\n#if IS_ENABLED(CONFIG_RELAY)'+s[body:end]+'\n#endif'+s[end:]
    return s
edit(mt/'mt7915/debugfs.c',debug)
(work/'noflash-compat.diff').write_text('\n'.join(changes))
marker.write_text('5.10.252 genl multicast API adaptation; duplicate macro guard; optional binary firmware relay log disabled when CONFIG_RELAY=n. No RF/power/data-path modifications.\n')
print(marker.read_text())
