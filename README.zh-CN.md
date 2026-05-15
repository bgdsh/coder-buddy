# 代码伙伴 Coder Buddy

代码伙伴是一个面向 AI 编程工作流的 ESP32-S3 实体提醒设备。当 AI 助手需要用户审批、授权、处理 review、或者等待用户注意时，它可以点亮 RGB LED、驱动舵机、播放 WAV 提示音，让“需要你看一眼”的状态变成一个真实的桌面提醒。

English documentation: [README.md](README.md)

本项目包含：

- ESP32-S3 MicroPython 固件
- 由设备直接提供的自包含 Web UI
- WAV 提示音生成与上传工具
- 无运行时 npm 依赖的 stdio MCP server
- 可复制安装的 AI agent skill 入口
- Playwright 与 MCP 冒烟测试

## 功能

- REST API：触发、停止、重置、查看提醒状态
- 中文 Web UI：`/` 和 `/index.html`
- 浏览器里选择 WAV 提示音轨
- 支持舵机、RGB LED、实体按钮、I2S 功放
- 实体紧急清除按钮：一键把提醒等级归零
- MCP 工具，方便 AI agent 集成：
  - `coder_buddy_trigger`
  - `coder_buddy_stop`
  - `coder_buddy_reset`
  - `coder_buddy_status`
  - `coder_buddy_set_track`

## 硬件

当前固件面向运行 MicroPython 的 ESP32-S3 开发板。

### 材料清单

| 材料 | 数量 | 说明 |
| --- | ---: | --- |
| ESP32-S3 开发板 | 1 | 需要 USB 串口能力。当前设备已在 16MB Flash、8MB PSRAM 的 ESP32-S3 上验证。 |
| 连续旋转舵机 | 1 | GPIO 14 输出 PWM 控制。位置舵机也可使用，但需要调整角度常量。 |
| 共阴 RGB LED | 1 | 红、绿、蓝三路分别接 PWM 引脚。按实际 LED 和供电加限流电阻。 |
| 轻触按钮 | 1 | 紧急清除按钮，GPIO 7，低电平有效。 |
| I2S 功放模块 | 1 | 用于播放 WAV 提示音，例如 MAX98357A 类 I2S 功放模块。 |
| 扬声器 | 1 | 阻抗和功率需要匹配功放模块。 |
| 外部 5V 电源 | 1 | 建议给舵机和功放供电，并与 ESP32-S3 共地。 |
| 面包板或洞洞板 | 1 | 用于原型搭建或固定焊接。 |
| 杜邦线 | 若干 | 舵机供电线尽量整理清楚，减少噪声影响。 |
| RGB LED 限流电阻 | 3 | 阻值取决于 LED 规格和供电电压。 |

默认 GPIO 映射：

| 功能 | GPIO |
| --- | --- |
| 舵机 PWM | 14 |
| RGB LED 红色 | 4 |
| RGB LED 绿色 | 5 |
| RGB LED 蓝色 | 6 |
| 紧急按钮 | 7 |
| I2S DIN | 16 |
| I2S BCLK | 17 |
| I2S LRC | 18 |
| 功放 enable / SD | 15 |

连线图、电源和共地说明见 [docs/wiring.md](docs/wiring.md)。

## 仓库结构

```text
.
├── AGENTS.md                 # 面向 coding agent 的维护说明
├── SKILL.md                  # 面向 agent 的 skill 指令
├── coder_buddy_mcp.mjs       # 无运行时依赖的 stdio MCP server
├── src/
│   ├── config.py             # 硬件引脚和固件配置
│   ├── main.py               # MicroPython 固件
│   ├── index.html            # 设备端 Web UI
│   └── secrets.example.py    # Wi-Fi 配置模板
├── audio/                    # 生成的 WAV 提示音
├── scripts/                  # 上传、音频生成和测试脚本
└── docs/                     # 硬件文档
```

## 环境要求

固件部署需要：

- Python 3
- `pyserial`
- `esptool`
- ESP32-S3 MicroPython 固件镜像
- 从 `src/secrets.example.py` 复制出的本地 `src/secrets.py`

UI 和 MCP 测试需要：

- 建议 Node.js 18+
- npm
- Playwright Chromium，可通过 `make check-ui-setup` 安装

## 配置 Wi-Fi

上传固件前先创建本地 Wi-Fi 配置：

```bash
cp src/secrets.example.py src/secrets.py
```

然后编辑 `src/secrets.py`，填入你的 Wi-Fi SSID 和密码。该文件已被 git 忽略，不要提交真实密码。

## 常用命令

列出串口：

```bash
make list-ports
```

识别已连接的 ESP32：

```bash
make identify PORT=/dev/cu.usbmodem101
```

刷入 MicroPython：

```bash
make flash PORT=/dev/cu.usbmodem101
```

上传固件代码、Web UI 和 WAV 资源：

```bash
make upload PORT=/dev/cu.usbmodem101
```

检查已部署设备状态：

```bash
make status
```

指定设备 IP：

```bash
make status BUDDY_IP=192.168.31.219
```

## REST API

默认 base URL：

```text
http://192.168.31.219
```

接口：

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `POST` | `/trigger` | 提醒等级 +1，最高 10。 |
| `POST` | `/stop` | 提醒等级 -1；降到 0 时停止提醒。 |
| `POST` | `/reset` | 提醒等级清零。 |
| `GET` | `/status` | 返回当前状态 JSON。 |
| `GET` | `/tracks` | 列出可用 WAV 音轨。 |
| `POST` | `/config/track` | 保存选中的 WAV 音轨。 |

示例：

```bash
curl -s -X POST http://192.168.31.219/trigger
curl -s http://192.168.31.219/status
curl -s -X POST http://192.168.31.219/reset
```

## Web UI

上传后在浏览器打开：

```text
http://192.168.31.219/
```

ESP32 会从 `/index.html` 提供 `src/index.html`。页面是自包含 HTML/CSS/JavaScript，通过 AJAX 调用固件 API。

## MCP Server

仓库根目录提供一个和 `SKILL.md` 同级的无依赖 stdio MCP server：

```bash
BUDDY_IP=192.168.31.219 node coder_buddy_mcp.mjs
```

仓库内使用：

```bash
make mcp
make check-mcp
```

`make check-mcp` 会通过 stdio 启动 MCP server，检查工具列表，并调用 `coder_buddy_status` 读取设备状态。

## Agent Skill

`SKILL.md` 和 `coder_buddy_mcp.mjs` 是 Coder Buddy skill 的 source of truth。同步到本机 agent skill 目录：

```bash
make sync-skill
make check-skill-sync
```

会安装到：

```text
~/.agents/skills/coder-buddy-esp32/
~/.claude/skills/coder-buddy-esp32/
```

安装后的 skill 文件夹是自包含的：只需要 `SKILL.md`、`coder_buddy_mcp.mjs` 和 Node.js。

## 测试

首次安装 UI 测试依赖和 Chromium：

```bash
make check-ui-setup
```

运行 Web UI 冒烟测试：

```bash
make check-ui
```

运行 MCP 冒烟测试：

```bash
make check-mcp
```

修改 UI 或 agent 集成逻辑后，建议运行这两类测试。

## 开发说明

- 固件行为放在 `src/main.py`，硬件映射放在 `src/config.py`。
- Web UI 保持自包含，放在 `src/index.html`，设备端不要依赖 CDN 或构建产物。
- `SKILL.md` 保持精简，只写 agent 需要使用的信息。
- `coder_buddy_mcp.mjs` 保持无运行时 npm 依赖，这样复制出的 skill 文件夹可以脱离仓库运行。
- 维护、部署、硬件和排障细节见 [AGENTS.md](AGENTS.md)。

## License

当前尚未声明许可证。正式接受外部贡献或发布 release 前，请先添加开源许可证。
