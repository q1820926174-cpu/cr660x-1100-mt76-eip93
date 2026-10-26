# CR660x 1100MHz / mt7915e / EIP-93 实验版源码

这是小米 CR660x 的实验固件改动与打包工具，适用于 PB-Boot 的 **firmware 更新入口**。它不是 PB-Boot 引导程序，也不包含引导程序二进制或源码。

提供源码、内核配置、版本锁定、原生无线启动服务，以及 **PB-Boot 可识别的完整 firmware `.bin`**，包含内核、完整根文件系统、LuCI 后台、默认网络配置和现有插件。[含插件完整镜像下载](https://github.com/q1820926174-cpu/cr660x-1100-mt76-eip93/releases/tag/v0.3.0-plugins-experimental)，使用说明见 [FIRMWARE.md](FIRMWARE.md)，插件范围见 [PLUGINS.md](PLUGINS.md)。

公开镜像从原作者公开的 5.4 基础固件重新打包，整合内核、驱动、配置界面及经过程序文件白名单筛选的插件。插件的私人配置、运行记录和自定义规则不会复制；Passwall 默认配置及规则从匹配的公开源码重建。未将私人 merged rootfs 或配置备份整体作为底包。**仅完成离线格式、模块、目标用户态程序和隐私检查，尚未刷入实机验证此公开镜像的首次启动。2.4GHz 故障仍未解决，不能当作稳定发行版。**

## 内容与实测状态

| 项目 | 当前状态 |
| --- | --- |
| 平台 | MT7621，256MiB DDR3，128MiB NAND，CR660x |
| CPU | 实机内核 1100MHz；未修改 DDR 频率 |
| 内核 | Linux 5.10.252；匹配 GCC 8.4.0 / musl；必须保留 `-fno-caller-saves` |
| Wi-Fi | mt7915e，mt76 2023-09-11 / backports 5.15.162-1 |
| 5GHz | 实机可连接并通过局域网传输测试；不保证所有环境的覆盖或速度 |
| 2.4GHz | **关联失败未解决**，不能视为已修复的无线固件 |
| EIP-93 | AES ECB/CBC/CTR 已通过硬件向量与软件对照测试；未启用 DES、AEAD |
| AES 性能 | 生产流量 CPU 开销、代理吞吐收益尚未做受控对照 |
| 公开版固件 | 完整镜像已生成、解包复核通过；尚未进行实机首次启动验证 |

1100MHz 已在一台设备上启动，不代表所有芯片或电源条件都稳定。此前实验内核曾启动失败，缺失编译选项已纠正，但不能据此认定已证明全部失败原因。此版本需要具备现场恢复条件，不宜当作稳定发行版。

## 目录

- `sources.lock.json`：上游仓库、提交和归档校验值。
- `patches/`：CPU 改动和 backports/mt76 兼容改动。
- `config/`：当前内核配置。
- `overlay/`：当前原生 hostapd/procd 启动代码。
- `public-overlay/`：公开版 LAN/WAN、Wi-Fi 初始配置和 LuCI 原生驱动设置页。
- `plugins.lock.json`：经隐私审核的插件程序组件包及版本锁定。
- `build/`：从实际构建脚本整理的参数化版本；环境准备见 [BUILD.md](BUILD.md)。
- `tools/pack-pbboot.py`：从独立提供的内核及 UBI 文件生成 PB-Boot firmware 镜像，不连接设备。
- `tests/`：AES 自检代码与公开文件检查。

## 隐私与许可证

采用新建空目录、逐项加入源码的方式发布；完整镜像从校验过的公开底包组装，没有复制私人镜像再尝试“删掉密码”。不包含原用户的 root 密码或散列、SSID/无线密码、代理订阅/节点、密钥、设备 MAC/序列号、Factory/EEPROM、NVRAM/Bdata、系统备份或原始诊断日志。公开的 Wi-Fi 初始密码在说明中列出，它不是任何原用户的密码。不要向此仓库提交实机配置。

本仓库自有集成代码按 GPL-2.0-or-later 开放；已有 SPDX 的文件及补丁保留原许可证，详见 [NOTICE](NOTICE)。上游项目仍按其自己的许可证分发。没有重新授权任何厂商二进制。

`PUBLICATION-AUDIT.json` 记录公开源码的隐私检查范围，`SHA256SUMS` 给出源码文件校验值。完整镜像的哈希、解包文件清单、软件包列表和隐私审计另附在 Release。可运行 `python3 tests/check-public-tree.py` 和 `python3 tests/test-pack-pbboot.py` 复核源码边界和打包格式。

## AES 并不等于 VLESS 加速

驱动适用于调用 Linux 内核 Crypto API 的消费者，无法自动把用户态 TLS/REALITY 加密搬到硬件。这版驱动有条件地对不超过 256 字节的小请求回退软件；这不等于按代理协议智能选择。VLESS 常见实现的加密路径不能仅靠安装该模块获得加速，GCM/AEAD 也未在本版启用。开机自检只运行一次，不是持续测速服务。

上游：[LEDE](https://github.com/Heleguo/lede)、[mt76](https://github.com/openwrt/mt76)、[EIP-93](https://github.com/vschagen/mtk-eip93)、[Xray TLS 实现](https://github.com/XTLS/Xray-core/blob/main/transport/internet/tls/config.go)。
