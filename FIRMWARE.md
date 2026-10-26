# 完整 PB-Boot 刷机包

下载 Release `v0.2.0-full-experimental` 中的：

```text
cr660x-1100-mt76-aes-public-experimental-factory.bin
```

这是完整固件，包含内核、根文件系统、LuCI 后台、LAN/WAN、DHCP/DNS、防火墙、PPPoE 支持，以及原生无线与 AES 模块；不是仅内核，也不是 PB-Boot 自身。大小 13,369,344 字节（12.75MiB）。

**状态：实验版，离线检查通过，尚未刷入实机验证这一公开包的首次启动。2.4GHz 关联失败尚未修复。** 原开发设备的 1100MHz、5GHz 和 AES 测试通过，不能代替此新镜像的完整验收。

## 刷入与首次使用

1. 仅用于已经核对布局的 Xiaomi CR660x（CR6606/6608/6609 同板家族）；需要有现场 PB-Boot 恢复条件。
2. 下载 `.bin` 及对应 `.sha256` 核对 SHA256。进入 PB-Boot 后使用 **firmware/固件更新入口** 上传完整 `.bin`。不要选择 Bootloader/EEPROM/Factory 写入入口，也不要把它当作普通 sysupgrade tar。
3. 使用 LAN 网线连接，电脑自动获取 IP；管理地址为 **http://192.168.50.1/**。WAN 默认为 DHCP；需要拨号时在 LuCI 网络接口中填写自己的 PPPoE 账号。
4. 管理用户名 **root**，首次登录为空密码，立即在“系统 → 管理权”设置管理员密码。
5. 5GHz 名称 **CR660X_5G**，初始 WPA2 密码 **cr660x-setup**；这是公开安装密码，需要修改。无线设置在“网络 → CR660x Native Wi-Fi”。2.4GHz 名称为 CR660X_2G，但连接故障仍未解决，不要依赖它上网。
6. 默认国家代码 CN，使用前按设备实际所在地修改。界面提供固定信道，不提供解除射频校准或监管限制的选项。

包中没有任何个人宽带账号、代理节点/订阅或 VPN 密钥。它包含公开上游底包的基础应用，不是作者私人系统全部额外安装插件的克隆；例如不包含私人 Passwall 安装及其配置。

## 保留与清除

包不包含 Bootloader、Factory/EEPROM、NVRAM、Bdata 分区，打包范围为 4MiB 内核分区加 UBI。硬件 MAC 与校准应由各设备自己的分区读取，未烧入开发设备身份。

此公开包使用干净的 rootfs_data，刷入会用公开默认配置启动。原系统的应用配置不包含在包中；需要保留时请先单独备份，不要把私人备份提交到 GitHub。

## 验证与限制

已核对 uImage CRC、内核分区界限、UBI EC/VID CRC 和几何、空白用户覆盖层；129 个模块的 vermagic/符号依赖通过。通过 QEMU 运行实际 MIPS Lua 和 UCI 验证配置生成、引号转义和控制字符拒绝。最终 `.bin` 已重新提取 squashfs，1,746 个普通文件逐项与干净构建目录比对，另扫描已知私人值与私钥。内核编译身份使用通用 builder/buildhost。

Release 附有 `FIRMWARE-PRIVACY-AUDIT.json`、`FIRMWARE-FILE-MANIFEST.json`、`PACKAGES.txt` 和构建校验报告。隐私扫描记录了一个与原公开底包逐字节相同的基础脚本中的公共默认值碰撞，不是从个人配置复制的内容。

未执行本次实机刷入、完整首次启动、无线射频或真实 WAN 吞吐验收。AES 对 VLESS/TLS/REALITY 的加速与 CPU 降负载收益没有得到证明。请根据实验状态使用，不能将离线通过理解为“保证刷完一切正常”。
