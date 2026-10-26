# 现有插件版

`v0.3.0-plugins-experimental` 在完整干净基础固件上补入 42 个已安装软件包和依赖。完整列表、版本及可复用程序组件包哈希见 `plugins.lock.json`，整机列表见 Release 的 `PLUGIN-PACKAGES.txt`。

| 功能 | 版本/处理 |
| --- | --- |
| Passwall | 26.5.11；Lua/UI、默认配置和规则由对应公开源码重建，保留原包版本记录；不是私人改动的逐字节克隆 |
| Xray | 26.5.9，目标程序版本查询和干净配置校验通过 |
| DDNS.to | 客户端 4.2.1，LuCI 4.0.3；关闭、令牌为空 |
| KMS/vlmcsd | 客户端软件包 2020.03.30~e5990804-r8；LuCI 控制页保留，服务默认关闭 |
| 代理辅助程序 | ChinaDNS-NG、dns2socks、dns2tcp、ipt2socks、microsocks、Shadowsocks/SSR、simple-obfs、tcping 等 |
| 工具与库 | tcpdump、unzip、coreutils、Lua UCI/YAML 绑定及对应动态库 |
| 基础功能 | 主题/主题设置、文件传输、ARP 绑定、UPnP、WOL、Turbo ACC 等继续来自干净底包 |
| 无线设置 | 使用与 mt7915e 匹配的 CR660x Native Wi-Fi 页面 |

保留干净基础包中已经满足依赖的系统包版本，不将旧 iptables/证书包覆盖到基础系统。未将标记为已卸载的软件或旧闭源无线驱动重新装回。

## 隐私边界

旧版公开安装包部分已下架。组件包按原软件包 `.list` 和安装状态逐项选取程序/库/界面资源，排除原 `.conffiles`、全部原 `/etc/config`、缓存/日志、私钥、证书、自定义数据文件和可编辑规则。没有把私人文件系统整体作为基础固件。

Passwall 配置与规则另从公开提交 `32ac46d42911453da27ced0247e70156016e0a4f` 重建；DDNS.to/KMS 使用本仓库生成的关闭状态空模板。私人服务器、订阅、账号、令牌、节点密钥、历史规则、MAC 和校准分区不包含在包内。初始网络与 Wi-Fi 配置见 FIRMWARE.md。

代理、远程访问和 KMS 需要使用者自行配置后启用。额外网络服务不因安装而直接启用。重新发布第三方程序不改变其原有许可证；DDNS.to 等第三方组件并不因本项目而成为自有开源代码，原组件信息保留在组件包清单中。

Release 同时附可复用的 `cr660x-clean-plugin-programs.tar.gz`。它是经过筛选、配置重置和解包复核的组件包，不是系统备份。使用该组件包重建公开固件不需要私人原始备份。

仍未完成这份公开镜像的实机首次启动和各插件的完整界面/真实网络验收；2.4GHz 故障仍存在。
