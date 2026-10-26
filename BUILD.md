# 构建说明与边界

这些脚本依赖已准备好的 LEDE Linux 5.10.252 构建树和 SDK，完成组件编译后可以组装完整公开镜像。完整镜像的根文件系统取自哈希锁定的公开上游 5.4 固件，不依赖私人系统快照。这里不是将所有上游应用都从源码重新编译的独立构建系统；从空环境准备全部依赖的端到端流程仍未验证。

## 工作目录

使用 Linux 或 WSL（bash、Python 3、make、patch、CMake、交叉工具链、LEDE host tools）。不要以 root 运行源码构建。示例：

```sh
export CR660X_KIT="$PWD"
export CR660X_WORK="$PWD/work"
export CR660X_OUTPUT="$PWD/out"
mkdir -p "$CR660X_WORK" "$CR660X_OUTPUT"
```

`$CR660X_WORK/source` 是 `sources.lock.json` 指定提交的 Heleguo/lede，`$CR660X_WORK/sdk` 是 OpenWrt SDK 21.02.7 ramips/mt7621 GCC 8.4.0 musl。此处的目录名要与脚本一致。先从官方下载页取得 SDK 并核对官方校验值。

将 `patches/999-cr660x-cpu-1100mhz.patch` 加入该树的 `target/linux/ramips/patches-5.10/`。先完成上游 host tools、工具链配置及 `target/linux/prepare`，让以下路径包含已打补丁内核：

```text
source/build_dir/target-mipsel-openwrt-linux-musl_musl/linux-ramips_mt7621/linux-5.10.252
```

将 `config/kernel-5.10.252.config` 用作该内核配置；必须使用与该内核完全一致的模块，不能拿其他发行版的同版本模块替换。`CONFIG_MODVERSIONS`、导出符号和内核 ABI 都需要核对。

## 内核及设备树

从上游 DTS/DTSI 编译 CR660x DTB，**不要从实机备份提取含设备属性的 DTB 用于公开发行**。`reference/` 中给出上游板级 DTS 供核对，它还依赖原树的 DTSI 和 dt-bindings。指定该干净编译产物：

```sh
export CR660X_DTB=/absolute/path/to/clean-built-cr660x.dtb
bash build/rebuild-hardware-baseline.sh
```

脚本用 `-fno-caller-saves` 重建，并追加 DTB、LZMA loader 和 uImage。输出到 `out/hardware-baseline-20261026/`。不要省略该选项，也不要混用上次构建留下的对象文件。

## 原生无线模块

```sh
bash build/prepare-mt76-noflash.sh
python3 build/apply-openwrt-patches.py
python3 build/patch-mt76-noflash-compat.py
bash build/build-mt76-noflash.sh
bash build/build-mt76-test-userspace.sh
bash build/compile-mt76-test-userspace.sh
```

归档会核验锁定哈希，OpenWrt 补丁树固定提交。兼容补丁必须在上游补丁之后、第一次编译之前应用。它调整 genl multicast API、宏重复定义、独立 CMAC 依赖和可选 RELAY 调试日志，未改射频功率或接收/发送算法。

无线固件取自锁定 mt76 源码的 `firmware/mt7915*.bin`，按其上游许可证使用；本仓库不重新分发这些 blob。regdb 使用 `build/prepare-mt76-regdb.sh` 的固定版本。country code 必须按设备所在地设置，不提供解除监管或校准限制的补丁。

## EIP-93

将锁定提交的 `vschagen/mtk-eip93` 源码放到：

```text
work/eip93/mtk-eip93-ca08387bf8352652129019bb19e2423ab313d5cb/
```

```sh
bash build/rebuild-baseline-eip93.sh
"$CR660X_WORK/sdk/staging_dir/toolchain-mipsel_24kc_gcc-8.4.0_musl/bin/mipsel-openwrt-linux-musl-gcc" \
  -O2 -static -march=mips32r2 -msoft-float tests/test-eip93-aes.c \
  -o "$CR660X_OUTPUT/eip93-aes-selftest"
```

AES-only 配置及 256 字节软件回退阈值见脚本。测试程序包含公开已知答案测试向量，不包含设备密钥。

## 干净文件系统和 PB-Boot 镜像

必须从上游构建出不含个人信息的 rootfs，再把新模块、工具、固件及 `overlay/` 以正确权限整合进去。原生模块启动顺序、安装位置和必要的软件包见 `build/INTEGRATION.md`。不要使用实机导出的 merged rootfs、overlay 或备份作为公开 rootfs。

原兼容模式从 Wi-Fi profile 读取 `SSID1`、`WPAPSK1`、`CountryCode`、`Channel`。不要复制开发者 profile。未配置合法 profile 或公开版 UCI 配置时服务会退出，不会生成无密码 AP。

以上是原兼容 profile 模式。完整公开版使用 `public-overlay/etc/config/cr660x_native` 和新 LuCI 页面，初始值与登录方式明确列在 [FIRMWARE.md](FIRMWARE.md)。配置生成器优先读取此文件，支持 UCI 引号转义，不依赖额外的 libuci-lua。初始 Wi-Fi 密码用于安装，须由使用者修改。

用上游 `mksquashfs4` 生成 squashfs，再运行同一 LEDE 树的 `scripts/ubinize-image.sh`：

```sh
TOPDIR="$CR660X_WORK/source" PATH="$CR660X_WORK/source/staging_dir/host/bin:$PATH" \
  sh "$CR660X_WORK/source/scripts/ubinize-image.sh" \
  --rootfs /path/to/clean-rootfs.squashfs /path/to/clean-rootfs.ubi \
  -p 128KiB -m 2048 -E 5
python3 tools/pack-pbboot.py \
  --kernel /path/to/kernel.uimage --ubi /path/to/clean-rootfs.ubi \
  --output out/cr660x-experimental-factory.bin
```

这个低级打包工具验证格式，**不会检查任意输入 rootfs 是否藏有私人数据**。格式正确也不保证可启动。私人恢复镜像禁止直接上传。

PB-Boot 需要 firmware 格式：4MiB 内核分区填充后接 UBI；不能将 sysupgrade tar 当作此格式。工具不会写 Bootloader/Factory，也没有远程刷机命令。实机更新必须确认板型、布局及恢复入口。

## 当前完整公开版的组装入口

先完成前述匹配组件的构建，再执行：

```sh
python3 build/fetch-public-base.py --output "$CR660X_WORK/upstream-5.4-sysupgrade.bin"
bash build/prepare-public-kernel.sh
python3 build/build-public-firmware.py \
  --base-sysupgrade "$CR660X_WORK/upstream-5.4-sysupgrade.bin" \
  --components "$CR660X_WORK" \
  --kernel "$CR660X_OUTPUT/kernel.uimage" \
  --work "$CR660X_WORK/public-assembly-new" \
  --output "$CR660X_OUTPUT/cr660x-1100-mt76-aes-public-experimental-factory.bin"
```

组装目录必须不存在。使用系统 `squashfs-tools` 的 `unsquashfs` 解包，以避免旧 SDK squashfskit 的退出状态问题。脚本校验原始公开输入哈希，安装两个 overlay，移除 vendor 无线模块、厂商默认密码脚本和预置身份密钥，核对所有模块符号，并通过 QEMU 执行目标 Lua。`prepare-public-kernel.sh` 从公开 DTS 重新编译设备树，使用通用编译身份重新链接内核。

本次 Release 的最终 `.bin` 另外解包并完成全部文件、空白覆盖层和敏感值审计；不等于完成实机首次启动。具体检查边界和完整软件包清单附在 Release。
