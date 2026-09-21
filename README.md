# YYS-AUTO

> 阴阳师（Onmyoji）手游自动化辅助工具 · v2.15

基于 **Python + OpenCV + ADB + Tkinter** 的手游自动化工具。通过 ADB 截图与模板匹配识别游戏界面，自动完成刷图、组队、爬塔、斗技等日常玩法的点击流程，支持多设备并行、参数持久化与任务完成通知。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey)

> **说明**：本项目的**代码部分与本文档**均由 **AI 辅助制作**（模板图片、使用文档等素材不在此列），可能存在疏漏或不完善之处，欢迎通过下方反馈渠道指正。

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [场景说明](#场景说明)
- [快捷键](#快捷键)
- [菜单栏说明](#菜单栏说明)
- [目录结构](#目录结构)
- [配置文件说明](#配置文件说明)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [反馈与交流](#反馈与交流)
- [免责声明](#免责声明)
- [License](#license)

---

## 项目简介

YYS-AUTO 是一款面向《阴阳师》手游的桌面自动化辅助工具。程序运行在 Windows 上，通过 **ADB** 与 Android 模拟器中的游戏通信：

1. **截图**：使用 `adb exec-out screencap` 获取设备画面；
2. **识别**：使用 OpenCV 模板匹配（`cv2.matchTemplate` + `TM_CCOEFF_NORMED`）判断当前处于哪个游戏界面；
3. **操作**：使用 `adb shell input tap` 在识别到的坐标处点击。

整个流程闭环运行，识别到目标界面即执行对应点击，直到达到设定的挑战次数或用户手动停止。

程序采用 **tkinter 选项卡（Tab）架构**，每一个标签页对应一台模拟器设备，可同时管理多台设备并行挂机。

> 本项目为个人兴趣作品，其中**代码与本文档均由 AI 辅助生成**（模板图片、使用文档等素材为作者自行整理制作），因此代码风格、实现方式可能存在不一致之处，欢迎反馈与建议。

---

## 功能特性

| 特性 | 说明 |
| --- | --- |
| **15 种场景预设** | 内置业原火、魂土单人、司机、队员、斗技、道馆、困28（单人/队长/队员）、英杰试炼、御灵、契灵、大富翁、结界突破、活动爬塔，一键切换 |
| **挑战计数器** | 精确记录每次挑战次数，可设定目标上限；达到上限自动停止，支持「0 = 无限循环」 |
| **司机-队员联动** | 司机发起邀请后队员自动接受，自动同步组队流程，无需手动协调 |
| **多设备并行** | 选项卡式 UI，每个标签页独立控制一台设备，支持批量「一键应用到所有」 |
| **绘卷模式** | 在「结界突破」与「困28单人」之间智能互切，提升绘卷刷取效率 |
| **被顶号自动处理** | 全局最高优先级。检测到被顶号后自动重启游戏、等待可配置秒数并重新进入 |
| **自动关闭加成** | 达成指定次数后强制重启游戏进程，关闭当前生效的经验/金币加成 |
| **走神模式**（V2.15） | 随机暂停当前标签页的识别与点击，模拟真人无法实时盯屏的行为；支持白名单场景 |
| **系统级通知** | 任务完成/异常时推送 Windows Toast 通知，优先 `winotify`，未安装回退 PowerShell 托盘通知 |
| **提示音** | 内置 6 种 WAV 提示音，任务结束后自动播放 |
| **识图性能优化** | `image_accelerator.py` 提供 Numba JIT 并行灰度转换与模板匹配、PyTurboJPEG 解码、raw 截图直转灰度；未安装依赖自动降级 OpenCV |
| **多线程匹配** | 模板匹配并行执行（主页可选 1~8 线程），利用 OpenCV 释放 GIL 的特性实现真正并行 |
| **模板缓存** | 模板图片一次性加载进内存缓存（`_template_cache`），避免重复磁盘读取 |
| **阈值独立记忆** | 每个场景独立记忆识别阈值，切换场景自动恢复；支持「重置默认」一键清除 |
| **可控日志记录** | 日志开关（默认关闭），可写入 `logs/` 目录，含 GUI / ADB / 识图三类日志 |
| **使用时长记录** | 按场景累计统计脚本运行时长，保存至 `usage_records.json` |
| **配置持久化** | 设备、端口、功能开关、窗口位置等全部保存到 `config.json`，重启自动恢复 |
| **安全退出** | 一键停止所有任务、关闭 ADB 服务进程、保存配置后退出，避免 ADB 进程残留 |

---

## 环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows |
| Python | 3.8 或更高版本 |
| 模拟器 | 支持 ADB 的 Android 模拟器（如 MuMu、雷电等） |
| 屏幕分辨率 | **1280 × 720（横屏）**，模拟器需设置为该分辨率 |
| 其他 | 模拟器中已开启 ADB 调试，并已安装《阴阳师》 |

> 程序在连接设备后会自动校验分辨率，要求**宽或高任意一边为 720**（例如 1280×720、720×1280），不满足时会给出提示。

---

## 安装

### 方式一：一键安装（推荐）

双击运行 [install.bat](file:///e:/ling/Documents/py/yys-auto/bat/install.bat)，脚本会自动配置清华 PyPI 镜像并安装全部依赖：

```bat
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
pip install --upgrade pip
pip install opencv-python numpy winotify
pip install numba PyTurboJPEG
```

### 方式二：手动安装

```bash
pip install opencv-python numpy winotify numba PyTurboJPEG
```

> `numba` 与 `PyTurboJPEG` 为**可选加速依赖**，用于提升识图速度。二者均为可选：未安装时程序会自动降级使用 OpenCV 原生实现。

### 启动程序

双击 [run.bat](file:///e:/ling/Documents/py/yys-auto/bat/run.bat) 启动。脚本会在启动失败时自动调用 `install.bat` 安装依赖后重试：

```bat
python ..\main.py
if errorlevel 1 (
    call install.bat
    python ..\main.py
)
```

也可直接运行主程序：

```bash
python main.py
```

---

## 快速开始

1. **配置模拟器**
   将模拟器分辨率调整为 **1280×720（横屏）**，并开启 ADB 调试。

2. **连接设备**
   在「设置」页填写模拟器的 ADB 地址与端口（默认 `127.0.0.1:16384`），点击连接。程序会自动检测设备与分辨率是否符合要求。
   > 常见端口：MuMu 为 16384、雷电为 5555，请以模拟器实际显示为准。

3. **选择设备与场景**
   切换到对应的设备标签页，选择需要的场景预设（如「业原火」「魂土单人」）。

4. **设置参数**
   - **识别阈值**：建议范围 `0.7 ~ 0.9`，默认 `0.8`；值越高越严格；
   - **运行次数**：目标挑战次数，`0` 表示无限循环；
   - **匹配线程数**：1~8，视 CPU 性能调整。

5. **启动**
   点击启动按钮（或按 `R`）开始运行。任务完成后会自动播放提示音并推送系统通知，所有设置自动保存，下次启动无需重新配置。

---

## 场景说明

项目共内置 **15 个场景预设**，另含 2 项全局辅助功能与 1 个走神模式。

| 场景 | 模块 | 模板目录 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| 业原火 | [yyh.py](file:///e:/ling/Documents/py/yys-auto/scenes/yyh.py) | `png/yyh` | 刷图 | Boss 刷图模式，自动点击战斗阶段，处理锁定、挑战、奖励界面 |
| 魂土单人 | [htdr.py](file:///e:/ling/Documents/py/yys-auto/scenes/htdr.py) | `png/htdr` | 刷图 | 含探索页与 Boss 段的自动导航，支持 5 种庭院探索页识别、宝藏领取与胜利结算 |
| 司机 | [sj.py](file:///e:/ling/Documents/py/yys-auto/scenes/sj.py) | `png/sj` | 组队 | 组队司机模式，负责发起挑战与发送邀请，与队员模块联动 |
| 队员 | [dy.py](file:///e:/ling/Documents/py/yys-auto/scenes/dy.py) | `png/dy` | 组队 | 组队队员模式，自动接受邀请、检测准备状态、追踪奖励获取 |
| 斗技 | [dj.py](file:///e:/ling/Documents/py/yys-auto/scenes/dj.py) | `png/dj` | PvP | 竞技场自动战斗，支持手动/自动模式切换，自动检测晋升与段位变化 |
| 道馆 | [dg.py](file:///e:/ling/Documents/py/yys-auto/scenes/dg.py) | `png/dg` | PvP | 道馆自动战斗，智能等待状态检测，自动识别挑战与结算界面 |
| 困28单人 | [k28.py](file:///e:/ling/Documents/py/yys-auto/scenes/k28.py) | `png/k28` | 爬塔 | 噩梦二十八层单人模式，支持屏幕滑动探索，可识别 Boss 与普通敌人路线 |
| 困28队长 | [k281.py](file:///e:/ling/Documents/py/yys-auto/scenes/k281.py) | `png/k281` | 组队 | 困28 队长版本，负责发起挑战与招募队友 |
| 困28队员 | [k280.py](file:///e:/ling/Documents/py/yys-auto/scenes/k280.py) | `png/k280` | 组队 | 困28 队员版本，被动跟随，自动接受邀请并追踪奖励 |
| 英杰试炼 | [yjsl.py](file:///e:/ling/Documents/py/yys-auto/scenes/yjsl.py) | `png/yjsl` | 爬塔 | 多阶段挑战模式，支持 5 种庭院探索页识别，自动通过各阶段关卡 |
| 御灵 | [yl.py](file:///e:/ling/Documents/py/yys-auto/scenes/yl.py) | `png/yl` | 刷图 | 御灵副本自动挑战，识别入口、挑战、胜利结算等界面 |
| 契灵 | [ql.py](file:///e:/ling/Documents/py/yys-auto/scenes/ql.py) | `png/ql` | 刷图 | 契灵结契自动化，支持「放弃结契 / 再次结契」两种模式（默认放弃结契） |
| 大富翁 | [dfw.py](file:///e:/ling/Documents/py/yys-auto/scenes/dfw.py) | `png/dfw` | 活动 | 大富翁活动自动化，识别出发、投掷、抢夺、挑战、奖励等节点；**不计挑战次数** |
| 结界突破 | [jjtp.py](file:///e:/ling/Documents/py/yys-auto/scenes/jjtp.py) | `png/jjtp` | 刷图 | 多步骤自动战斗流程，支持自动切换至/来自困28，是绘卷模式的核心场景 |
| 活动爬塔 | [hdpt.py](file:///e:/ling/Documents/py/yys-auto/scenes/hdpt.py) | `png/hdpt` | 活动 | 限时活动爬塔模式，自动识别退出界面并逐层攀登，持续适配新活动 |

**全局辅助功能**

| 名称 | 模块 | 说明 |
| --- | --- | --- |
| 关闭加成 | [guanbijiacheng.py](file:///e:/ling/Documents/py/yys-auto/scenes/guanbijiacheng.py) | 强制停止并重启游戏，清除当前生效的经验/金币加成 |
| 被顶号处理 | [dinghao.py](file:///e:/ling/Documents/py/yys-auto/scenes/dinghao.py) | 全局最高优先级。检测到顶号后关闭游戏、等待可配置秒数、重启并点击进入 |

**走神模式**（[zoushen.py](file:///e:/ling/Documents/py/yys-auto/scenes/zoushen.py)）

V2.15 新增。随机抽取触发时间到达后，暂停当前标签页的识别与点击，倒计时结束自动恢复。默认关闭，需在设置页手动开启；可配置触发间隔与持续时长，并支持设置**白名单场景**（白名单内的场景不触发走神）。

---

## 快捷键

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl` + `T` | 新建标签页 |
| `Ctrl` + `W` | 删除当前标签页 |
| `F2` | 重命名当前标签页 |
| `R` | 启动当前设备任务 |
| `S` | 停止当前设备任务 |
| `F5` | 全部开始 |
| `F6` | 全部停止 |
| `1` | 切换到「设置」页 |
| `2` ~ `9` | 依次切换到第 1~8 个设备标签页 |

> 输入框处于聚焦状态时会自动屏蔽快捷键，避免误触。

---

## 菜单栏说明

| 菜单 | 主要功能 |
| --- | --- |
| **程序(P)** | 重启程序、重启 ADB 并重启程序、关闭 ADB 并退出程序 |
| **设置(T)** | 司机-队员联动、关闭加成、绘卷模式、斗技晋升后停止、契灵结契方式、提示音、日志开关、走神模式等 |
| **标签(B)** | 新建 / 删除 / 重命名标签页 |
| **运行(R)** | 开始 / 停止、全部开始 / 全部停止、运行时长记录 |
| **帮助(H)** | 打开使用说明文档、快捷键说明、UU 远程官网、Bug 反馈与建议、关于 YYS-AUTO |

---

## 目录结构

```text
yys-auto/
├── main.py                    # 程序入口：GUI 主界面与自动化调度（tkinter）
├── adb.py                     # ADB 设备管理、分辨率校验与日志系统
├── image_recognizer.py        # 图像识别核心：模板匹配、缓存、多线程
├── image_accelerator.py       # 可选加速：Numba JIT / PyTurboJPEG / raw 截图解析
├── notification.py            # 系统通知（winotify Toast，回退 PowerShell）
├── wav.py                     # 提示音设置与播放
├── config.json                # 运行配置（设备、功能开关、窗口位置等）
├── usage_records.json         # 各场景使用时长统计
├── icon.ico                   # 程序图标
├── 清除程序数据.bat            # 删除 config.json，重置配置
│
├── bat/
│   ├── install.bat            # 安装依赖（清华源）
│   └── run.bat                # 启动程序，失败自动安装依赖后重试
│
├── scenes/                    # 场景模块，统一导出 handle_scene() 接口
│   ├── yyh.py                 # 业原火
│   ├── htdr.py                # 魂土单人
│   ├── sj.py / dy.py          # 司机 / 队员
│   ├── dj.py / dg.py          # 斗技 / 道馆
│   ├── k28.py / k281.py / k280.py   # 困28 单人 / 队长 / 队员
│   ├── yjsl.py                # 英杰试炼
│   ├── yl.py                  # 御灵
│   ├── ql.py                  # 契灵
│   ├── dfw.py                 # 大富翁
│   ├── jjtp.py                # 结界突破
│   ├── hdpt.py                # 活动爬塔
│   ├── guanbijiacheng.py      # 关闭加成
│   ├── dinghao.py             # 被顶号处理
│   └── zoushen.py             # 走神模式
│
├── png/                       # 识别模板图片
│   ├── yyh/ htdr/ sj/ dy/ dj/ dg/ ...
│   ├── dinghao.png            # 被顶号弹窗
│   └── jujue.png              # 拒绝悬赏
│
├── wav/                       # 提示音（QQ、Steam、iOS信息、iOS通知、言灵、骄阳长明）
├── platform-tools/            # 随附的 Android SDK platform-tools（含 adb.exe）
├── logs/                      # 日志输出目录（GUIlog_ / adb_ / image_）
└── 使用文档第一次使用必看/      # 图文使用说明与更新日志
```

---

## 配置文件说明

### config.json

程序退出时自动保存，主要包括：

| 字段 | 说明 |
| --- | --- |
| `last_tab` / `tabs` | 上次选中的标签页、各标签页配置（名称、场景预设、次数、线程数、阈值、设备） |
| `link_enabled` | 司机-队员联动开关 |
| `close_jiacheng_enabled` / `close_jiacheng_wait` | 关闭加成开关与等待秒数 |
| `dinghao_wait` | 被顶号后的等待秒数 |
| `huijuan_mode` | 绘卷模式开关 |
| `dj_jinsheng_stop` | 斗技段位晋升后是否结束程序 |
| `ql_fangqi` / `ql_zaici` | 契灵「放弃结契 / 再次结契」 |
| `sound_enabled` / `sound_file` | 提示音开关与音效文件 |
| `logging_enabled` | 详细日志开关（默认关闭） |
| `adb_ip` / `adb_port` | ADB 地址与端口 |
| `notify_enabled` | 系统通知开关 |
| `zoushen_*` | 走神模式相关设置 |

### usage_records.json

按场景记录累计运行时长，可通过菜单「运行 → 运行时长记录」查看。

---

## 常见问题

**Q：识别不到界面 / 频繁误点？**
调低识别阈值（建议 `0.7 ~ 0.9`），并确认模拟器分辨率与游戏界面语言、UI 布局与模板图一致；如游戏更新了界面，需要同步更新 `png/` 下的模板图片。

**Q：连接不上设备？**
1. 确认模拟器已开启 ADB 调试，端口填写正确；
2. 尝试菜单「程序(P) → 重启 ADB 并重启程序」；
3. 检查是否有其他 ADB 工具占用了 5037 端口。

**Q：提示分辨率不符合要求？**
在模拟器设置中将分辨率调整为 **1280×720（横屏）**，重启模拟器后重新连接。

**Q：程序运行异常，想恢复默认设置？**
关闭程序后运行 [清除程序数据.bat](file:///e:/ling/Documents/py/yys-auto/清除程序数据.bat)，该脚本会删除 `config.json`，下次启动即恢复默认配置。

**Q：识图速度慢？**
在主页适当提高匹配线程数；并确保已安装 `numba`、`PyTurboJPEG` 以启用加速模块。

**Q：任务完成后想要提醒？**
在设置页开启提示音与系统通知开关；未安装 `winotify` 时会自动回退为 PowerShell 托盘通知。

更多图文说明请查看 `使用文档第一次使用必看/` 目录。

---

## 更新日志

### v2.15（2026-09-17）
- 添加**走神模式**，可自定义触发时间与持续时间，白名单场景不触发；默认关闭，需在设置页手动开启
- 设备控制页标题处显示当前标签名称
- 优化一键启停日志输出
- 调整 `main` 结构，拆分部分功能代码
- 补充设置页的功能提示

### v2.14（2026-09-10）
- 适配周年庆爬塔
- 更新困28识别图片

### v2.13（2026-08-19）
- 删除武道日常场景
- 更新大富翁与活动爬塔场景；大富翁不计挑战次数

### v2.12（2026-08-14）
- 添加武道日常场景（仅适配活动 200 次）
- 添加**多线程匹配**，主页可自行选择线程数

### v2.11（2026-08-07）
- 添加**使用时长记录**（入口在运行菜单栏）
- 添加**契灵场景**，默认放弃结契，可在功能设置中改为再次结契

### v2.10（2026-08-04）
- 添加**御灵场景**
- 优化识图性能，提高速度

### v2.9（2026-07-25）
- 优化结界突破步骤，提升清突破券速度
- 添加**系统级通知**，任务完成或异常后推送提醒
- 添加**被顶号后重新进入游戏**功能，可设置等待秒数
- 控制页添加「一键应用所有」按钮
- 菜单栏「文件(F)」改名为「程序(P)」，新增重启程序、重启 ADB 并重启程序

更早版本的更新记录请查看 `使用文档第一次使用必看/更新日志.txt`。

---

## 反馈与交流

- **交流群**：`647871264`（群内 @群主）
- **邮箱**：haixingtaohai@163.com
- **GitHub**：<https://github.com/haixingtaohai/YYS-AUTO>
- **更新下载**：<https://wwbet.lanzoum.com/b00ct17efa>（网盘密码：`62m8`）

反馈时请尽量附上问题截图、日志文件（`logs/` 目录）以及当前使用的场景与版本号，便于快速定位问题。

---

## 免责声明

本项目仅供学习与交流使用，请勿用于任何商业用途。使用本工具产生的一切后果（包括但不限于游戏账号被封禁、数据异常等）由使用者自行承担。请遵守游戏官方的用户协议与相关规定，理性使用。

本项目的**代码与本文档均由 AI 辅助制作**（模板图片、使用文档等素材除外），作者已尽力测试主要功能，但无法保证在所有模拟器、分辨率与游戏版本下均能正常运行，使用前请自行评估风险。

---

## License

本项目采用 [CC BY-NC-SA 4.0（署名—非商业性使用—相同方式共享 4.0 国际）](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh) 许可协议。

您可以自由地：

- **共享** —— 在任何媒介或格式中复制和重新发布本作品
- **演绎** —— 修改、转换或以本作品为基础进行创作

惟须遵守下列条件：

- **署名（BY）** —— 您必须给出[适当的署名](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)，提供指向本许可协议的链接，并[标明是否作出了修改](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)。您可以以任何合理的方式这样做，但不得以任何方式暗示许可人为您或您的使用背书。
- **非商业性使用（NC）** —— 您不得将本作品用于[商业目的](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)。
- **相同方式共享（SA）** —— 如果您再混合、转换或者基于本作品进行创作，您必须基于[与原先许可协议相同的许可协议](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)分发您贡献的作品。

- **不得增加额外限制** —— 您不能增设法律条款或[技术措施](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)来限制别人做许可协议允许的事。

完整协议文本请见：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh>

Copyright (c) 2026 凌ling妻
