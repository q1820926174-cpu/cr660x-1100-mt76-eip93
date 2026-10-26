# 完整 PB-Boot 刷机包

下载 Release `v0.3.0-plugins-experimental` 中的：

```text
cr660x-1100-mt76-aes-plugins-public-experimental-factory.bin
```

这是完整固件，包含内核、根文件系统、LuCI 后台、LAN/WAN、DHCP/DNS、防火墙、PPPoE 支持、原生无线与 AES 模块，以及现有插件；不是 PB-Boot 自身。大小 25,821,184 字节（24.625MiB）。

**状态：实验版，离线检查通过，尚未刷入实机验证这一公开包的首次启动。2.4GHz 关联失败尚未修复。** 原开发设备的 1100MHz、5GHz 和 AES 测试通过，不能代替此新镜像的完整验收。

## 刷入与首次使用

1. 仅用于已经核对布局的 Xiaomi CR660x（CR6606/6608/6609 同板家族）；需要有现场 PB-Boot 恢复条件。
2. 下载 `.bin` 及对应 `.sha256` 核对 SHA256。进入 PB-Boot 后使用 **firmware/固件更新入口** 上传完整 `.bin`。不要选择 Bootloader/EEPROM/Factory 写入入口，也不要把它当作普通 sysupgrade tar。
3. 使用 LAN 网线连接，电脑自动获取 IP；管理地址为 **http://192.168.50.1/**。WAN 默认为 DHCP；需要拨号时在 LuCI 网络接口中填写自己的 PPPoE 账号。
4. 管理用户名 **root**，首次登录为空密码，立即在“系统 → 管理权”设置管理员密码。
5. 5GHz 名称 **CR660X_5G**，初始 WPA2 密码 **cr660x-setup**；这是公开安装密码，需要修改。无线设置在“网络 → CR660x Native Wi-Fi”。2.4GHz 名称为 CR660X_2G，但连接故障仍未解决，不要依赖它上网。
6. 默认国家代码 CN，使用前按设备实际所在地修改。界面提供固定信道，不提供解除射频校准或监管限制的选项。

包中没有个人宽带账号、代理节点/订阅、DDNS.to 令牌或 VPN 密钥。已补入 Passwall、Xray、DDNS.to、KMS 和依赖等 42 个软件包，基础应用继续保留。代理、远程访问及 KMS 默认关闭，由使用者填入自己的信息后启用，详见 [PLUGINS.md](PLUGINS.md)。

## 保留与清除

包不包含 Bootloader、Factory/EEPROM、NVRAM、Bdata 分区，打包范围为 4MiB 内核分区加 UBI。硬件 MAC 与校准应由各设备自己的分区读取，未烧入开发设备身份。

此公开包使用干净的 rootfs_data，刷入会用公开默认配置启动。原系统的应用配置不包含在包中；需要保留时请先单独备份，不要把私人备份提交到 GitHub。

## 验证与限制

已核对 uImage CRC、内核分区界限、UBI EC/VID CRC 和几何、空白用户覆盖层；129 个模块的 vermagic/符号依赖通过。通过 QEMU 运行实际 MIPS Lua/UCI、Xray 版本查询和无私人信息的配置校验，核对插件依赖、40 个 ELF 程序/库的动态库文件、设置页资源及启动脚本语法。最终 `.bin` 已重新提取 squashfs，2,265 个普通文件逐项与干净构建目录比对，另扫描已知私人值与完整私钥块。内核编译身份使用通用 builder/buildhost。

Release 附有 `PLUGIN-FIRMWARE-PRIVACY-AUDIT.json`、`PLUGIN-FIRMWARE-FILE-MANIFEST.json`、`PLUGIN-PACKAGES.txt` 和构建校验报告。隐私扫描中的公共默认值碰撞仅在与公开底包或已锁定公开源码逐字节一致的文件上豁免，并列入审计报告；这不代表复制了个人配置。

未执行本次实机刷入、完整首次启动、无线射频或真实 WAN 吞吐验收。AES 对 VLESS/TLS/REALITY 的加速与 CPU 降负载收益没有得到证明。请根据实验状态使用，不能将离线通过理解为“保证刷完一切正常”。
