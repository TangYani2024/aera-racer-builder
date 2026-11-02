# 给 racer 编 AERA Recovery：低成本方案

目标：不用在自己电脑上同步整套 AOSP，就能给 racer（XT2063-2）编出 AERA Recovery。

## 1. 成本对比

| 路线 | 同步量 | 磁盘 | 首次构建 | 本地成本 |
|---|---|---|---|---|
| 官方流程（全量 manifest） | 989 个项目，全历史 | 200 GB+ | 数小时 | 一台 Linux 大盘机器 |
| 最小同步（本方案） | 64 个项目，`--depth=1` | 预估 15–25 GB | 1–2 小时 | 0（跑在 GitHub 免费 runner 上） |
| 增量构建（改设备树后） | — | 复用 out/ | 几分钟 | 0 |

"官方流程贵"的原因不是产物大（recovery.img 只有几十 MB），而是 Android 构建系统要整树解析依赖：recovery 链接的平台库全散在源码里，`repo sync` 默认又全量拉。AERA 的 `remove-minimal.xml` 只删了模拟器和 x86 边角料，省不了多少，所以才需要自己再砍一层。

## 2. 本文件夹里的东西

```
racer-build/
├── BUILD_PLAN.md                        # 本文件
├── local_manifests/
│   └── remove-aera-minimal.xml         # v1.1：从 default.xml 的 989 个项目里删掉 925 个，只留 64 个
└── .github/workflows/
    └── build-aera-racer.yml            # GitHub Actions 构建流程
```

### 最小同步清单是怎么来的

直接对 AERA `default.xml` 做了减法：保留构建系统（build/make、build/soong、bionic）、recovery 及其 AERA 变体（bootable/recovery、system/core、adb、Connectivity、LVGL、vendor/recovery、vendor/twrp、device/qcom/twrp-common——解密用的 qcom_decrypt 就在里面）、它们的链接期依赖（frameworks/base、frameworks/native、hardware/interfaces、system/* 的一小部分、external/* 里约 50 个库、prebuilts 工具链），其余全部删掉。

两个有意的保守决定：

- **留了 `frameworks/base`**：基础产品配置文件会引用它，删掉是最可能让第一次构建直接炸在 lunch 阶段的原因。等构建跑通之后可以再试着砍。
- **留了 `prebuilts/vndk` 和 `prebuilts/sdk`**：recovery 链接的部分 VNDK 库和 Soong 宿主工具需要它们。

### 诚实说明：v1.1 未验证

这份清单没有跑通过。预期打法就是**用 CI 当验证器**：第一次跑大概率在某个缺失的项目上失败，日志会明确报出缺了谁 → 从 remove 清单里删掉那一行 → 重跑。1–3 轮是正常的。最可能要加回的候选：

- `system/netd`、 `external/dhcpcd`（如果 AERA 的联网功能需要它们）
- `art` / `libcore` / `libnativehelper`（如果某个基础产品配置引用了它们）
- `prebuilts/ndk`、更多的 `external/*` 小库

## 3. 使用步骤

1. **建一个 GitHub 仓库**（名字随意，如 `aera-racer-builder`），把本文件夹的全部内容推上去（`.github/workflows/` 和 `local_manifests/` 都要在）。
2. **先有 racer 的 AERA 设备树**（见第 4 节，前置条件）。树建好后，在 Actions 页面点 Run workflow，填它的仓库地址和分支（默认 `aera-16.0`）。
3. **等构建**：免费 runner 每月 2000 分钟额度，一次构建约 1–2 小时，在额度内。产物 `recovery.img` 会作为 artifact（保留 14 天）供下载。
4. **失败就修清单**：按第 2 节的方法删 remove 行、重跑。
5. **测试**：下载后先 `fastboot boot recovery.img` 临时启动，确认能进界面、触摸可用、能解密 /data 之后，再考虑刷进 recovery 分区。

## 4. 前置条件：racer 的 AERA 设备树

**骨架已搭好**：`~/workspace/aera/racer-tree/`（24 个文件，39 MB，主要是预编译内核）。

- `device/motorola/racer/`：产品定义、BoardConfig、fstab、预编译内核/DTB/DTBO（已从用户自己的 14-13 备份里提取并验证）、亮度值（来自内核面板 DTS，max 2047）、触摸模块清单（来自 LOS 树）
- `device/motorola/sm7250-common/`：平台共用部分（分区尺寸、内核参数、A/B 配置、recovery 初始化脚本）

还缺两块要真机才能补（树里的 `TODO.md` 有 exact 命令）：**① vendor 内核模块**（`extract-modules.sh` 一键从 LOS 手机里拉）和 **② 解密用的 QCOM 安全二进制**（qseecomd、keymint 等，从 LOS vendor 里提）。这两块补完之后，把两棵树各推到一个 GitHub 仓库，再跑上面的工作流。

## 5. 磁盘数学（为什么云构建能成立）

- GitHub 免费 runner（ubuntu-22.04）默认只有约 14 GB 空闲 → 工作流第一步用 `free-disk-space` 清掉 .NET、Android SDK、Haskell 等，腾到约 45–55 GB。
- 最小同步（depth=1）预估 15–25 GB；`out/` 约 5–10 GB。能放下，但不算宽裕。
- 如果还是爆盘，备选：自建 runner（任意 100 GB+ 磁盘的 Linux 机器，跑 `actions/runner` 接入同一个仓库），或租一台按小时计费的云主机。

## 6. 风险清单

- AERA 只有 7 周大、38 个 star，文档基本只有 manifest 的 README 和几台现成树；遇到问题主要靠自己读代码和看日志。
- 解密是最大未知数：LOS 23.2 的 /data 是 FBE 加密，AERA 继承 TWRP 的解密栈，garnet 上能用不等于 racer 上能用，要实测。
- racer 的 sm7250 + 4.19 内核 + 安卓 11 年代 vendor，是 AERA 支持列表里最老的一档；它的新功能（recovery 里跑流量要用的 qrtr/rmtfs 用户态）和老内核接口对不上的风险存在。
- 免费 runner 单次任务上限 6 小时，工作流已设 `timeout-minutes: 360`。

## 7. Manifest Validation

Before modifying `local_manifests/remove-aera-minimal.xml`, ensure its correctness by using the provided validation script.

Run the script from the repository root:

```bash
python3 tools/check_manifest.py local_manifests/remove-aera-minimal.xml
```

The script performs the following checks:
1. **XML is well-formed:** Fails if the file cannot be parsed as valid XML.
2. **No duplicate entries:** Fails if the same `remove-project` name is listed more than once. (Historically, a project was mistakenly removed multiple times, causing sync issues.)
3. **Valid AOSP prefix:** Fails if a project name does not start with a recognized AOSP prefix (e.g., `platform/`, `kernel/`, `hardware/`, etc.).
4. **Alphabetical ordering:** Emits a warning if the entries are not sorted alphabetically.

A successful validation exits with status `0`. Any errors will produce a non-zero exit status and print an explanation to stderr. You can test the script's behavior using the included fixture:

```bash
python3 tools/check_manifest.py tools/fixtures/duplicate.xml
```
