# CR660x 1100MHz / mt7915e / EIP-93 实验版源码

这是小米 CR660x 的实验固件改动与打包工具，适用于 PB-Boot 的 **firmware 更新入口**。它不是 PB-Boot 引导程序，也不包含引导程序二进制或源码。

当前公开的是源码、内核配置、版本锁定、原生无线启动服务和镜像打包工具。**没有发布可直接刷入的 `.bin`**：现有实机恢复包混有个人配置，不能作为公开发行镜像。公开干净镜像需要从干净的上游文件系统重新构建；本仓库尚未完成这一整条构建与首次启动验证，不承诺一键复现私人恢复包。

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
| 公开版固件 | 尚未生成、尚未刷机验证 |

1100MHz 已在一台设备上启动，不代表所有芯片或电源条件都稳定。此前实验内核曾启动失败，缺失编译选项已纠正，但不能据此认定已证明全部失败原因。此版本需要具备现场恢复条件，不宜当作稳定发行版。

## 目录

- `sources.lock.json`：上游仓库、提交和归档校验值。
- `patches/`：CPU 改动和 backports/mt76 兼容改动。
- `config/`：当前内核配置。
- `overlay/`：当前原生 hostapd/procd 启动代码。
- `build/`：从实际构建脚本整理的参数化版本；环境准备见 [BUILD.md](BUILD.md)。
- `tools/pack-pbboot.py`：从独立提供的内核及 UBI 文件生成 PB-Boot firmware 镜像，不连接设备。
- `tests/`：AES 自检代码与公开文件检查。

## 隐私与许可证

采用新建空目录、逐项加入源码的方式发布，没有复制私人镜像再尝试“删掉密码”。不包含 root 密码或散列、SSID/无线密码、代理订阅/节点、用户密钥、设备 MAC/序列号、Factory/EEPROM、NVRAM/Bdata、系统备份或原始诊断日志。不要向此仓库提交实机配置或镜像。

本仓库自有集成代码按 GPL-2.0-or-later 开放；已有 SPDX 的文件及补丁保留原许可证，详见 [NOTICE](NOTICE)。上游项目仍按其自己的许可证分发。没有重新授权任何厂商二进制。

`PUBLICATION-AUDIT.json` 记录本次公开源码的隐私检查范围，`SHA256SUMS` 给出发布文件校验值。可运行 `python3 tests/check-public-tree.py` 和 `python3 tests/test-pack-pbboot.py` 复核源码边界和打包格式。

## AES 并不等于 VLESS 加速

驱动适用于调用 Linux 内核 Crypto API 的消费者，无法自动把用户态 TLS/REALITY 加密搬到硬件。这版驱动有条件地对不超过 256 字节的小请求回退软件；这不等于按代理协议智能选择。VLESS 常见实现的加密路径不能仅靠安装该模块获得加速，GCM/AEAD 也未在本版启用。开机自检只运行一次，不是持续测速服务。

上游：[LEDE](https://github.com/Heleguo/lede)、[mt76](https://github.com/openwrt/mt76)、[EIP-93](https://github.com/vschagen/mtk-eip93)、[Xray TLS 实现](https://github.com/XTLS/Xray-core/blob/main/transport/internet/tls/config.go)。
