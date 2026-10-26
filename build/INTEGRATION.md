# rootfs 集成参考

仅针对这里锁定的 5.10.252 ABI，供干净构建时人工审核与集成。

| 文件 | 安装位置 |
| --- | --- |
| compat/cfg80211/mac80211/mt76/mt76-connac-lib/mt7915e/cmac 模块 | `/lib/modules/5.10.252/` |
| crypto-hw-eip93/cbc 模块 | `/lib/modules/5.10.252/` |
| mt7915_rom_patch、mt7915_wa、mt7915_wm | `/lib/firmware/mediatek/` |
| regulatory.db | `/lib/firmware/` |
| 静态 hostapd、hostapd_cli、iw | `/usr/sbin/` |
| AES 自检程序 | `/usr/libexec/eip93-aes-selftest` |
| overlay 文件 | 对应 rootfs 相对路径 |

脚本、hostapd/iw、自检程序需要 0755；Lua 文件可以 0644。生成的 hostapd 配置必须 0600。不要自动加载 vendor `mt_wifi`，也不要将旧 `/etc/modules.d/mt7915` 留在启用状态。不要对已启动的 vendor 驱动做热替换。

新增 modules.d：

```text
09-crypto-cbc: cbc
10-crypto-hw-eip93-aes: crypto-hw-eip93
20-cmac: cmac
25-mt76-native: compat cfg80211 mac80211 mt76 mt76-connac-lib mt7915e
```

上面最后一项在文件中每行写一个模块名。启用服务软链接 `S16eip93-selftest`、`S25cr660x-mt76`、`K89cr660x-mt76`，链接到对应 `/etc/init.d/` 文件。运行依赖包括 procd、Lua、kmod/modprobe、bridge/network 初始化以及 hostapd nl80211 支持。

此版保留 ra0/rax0 命名，用独立 procd 服务管理 hostapd。不能同时启用另一套自动管理这些接口的 hostapd/netifd 配置；厂商 LuCI 无线状态可能不反映这套驱动。LAN/WAN 应由干净上游网络默认配置初始化，不能复制作者网络或代理配置。
