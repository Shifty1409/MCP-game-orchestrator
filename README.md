# MCP 安全接入与游戏创作编排器

> 一个安全优先的 MCP 编排 Skill：自动发现本地已配置的 MCP 服务，经用户授权后接入，并引导完成游戏开发。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-compatible-blue)](https://modelcontextprotocol.io/)

---

## 这是什么

一个**平台无关**的提示词 Skill，适用于任何支持 system prompt 的 AI Agent（DSH、Claude Code、Cursor、Windsurf 等）。

它做三件事：

1. **发现**：扫描本地已知的 MCP 配置文件路径，列出可接入的服务
2. **接入**：展示权限、取得用户授权后建立连接
3. **创作**：收集游戏需求，基于已接入的 MCP 工具辅助开发

---

## 核心理念：安全边界

市面上不少 MCP 工具追求"一键接入"，但忽略了 MCP Server 本质是**高权限进程**——它能读写文件、执行命令、访问网络。

本项目选择反其道而行，**明确划出五条硬性边界**：

| 不做 | 原因 |
|---|---|
| ❌ 不遍历全盘 | 避免读取隐私文件、拖慢系统 |
| ❌ 不联网下载 | 避免供应链攻击 |
| ❌ 不静默接入 | MCP 是高权限进程，必须用户授权 |
| ❌ 不保存密钥 | Token/Key 一旦泄露后果严重 |
| ❌ 不执行未知代码 | 来源不明的 MCP 工具不调用 |

**一句话**：发现可以自动，接入必须确认，安装永不自动。

---

## 快速开始

### 方式一：作为 System Prompt 使用

1. 打开你的 AI Agent（DSH / Claude Code / Cursor 等）
2. 将 [`SKILL.md`](./SKILL.md) 的全部内容粘贴到 system prompt 或自定义指令中
3. 对话中输入：`帮我接入 MCP 并创建一个游戏`

### 方式二：作为 Skill 文件加载

如果你的平台支持 skill 文件目录：

```
your-skills/
└── mcp-orchestrator/
    └── SKILL.md
```

将 `SKILL.md` 放入对应目录，平台会自动加载。

### 方式三：克隆本仓库

```bash
git clone https://github.com/Shifty1409/mcp-game-orchestrator.git
```

---

## 辅助脚本（可选）

如果你不想让 Agent 自己扫描，可以先手动运行：

```bash
python3 scripts/scan_config.py
```

脚本会输出结构化的 JSON 结果，包含检测到的 MCP 服务。将这个结果粘贴给 Agent，直接进入授权确认流程。

**脚本的安全保证**：
- 只读白名单路径，不遍历全盘
- 不联网，不上传任何数据
- 不执行配置文件中的命令
- 不输出 token / env / 密码等敏感字段
- 不保存任何状态（仅打印到 stdout）

---

## 工作流程

flowchart TD
    A["开始"] --> B["步骤一：发现"]
    B --> B1["方式A：手动输入软件名"]
    B --> B2["方式B：白名单扫描"]
    B1 --> C{"检测到 MCP 服务?"}
    B2 --> C
    C -->|否| D["输出引导信息"]
    D --> B
    C -->|是| E["步骤二：授权确认"]
    E --> F{"用户授权?"}
    F -->|否| B
    F -->|是| G["建立 MCP 连接"]
    G --> H{"连接成功?"}
    H -->|否| I["输出错误 + 排查建议"]
    I --> B
    H -->|是| J["保存非敏感状态"]
    J --> K["步骤三：收集游戏需求"]
    K --> L{"用户确认?"}
    L -->|补充| K
    L -->|confirm| M["步骤四：分步开发"]
    M --> N["结构确认 -> 逐文件写入 -> 构建"]

---

## 预定义白名单

当前支持的 MCP 配置文件路径（详见 `examples/whitelist.json`）：

| 工具 | 路径 |
|---|---|
| Cursor | `~/.cursor/mcp.json` |
| Claude Code | `~/.claude/config.json` |
| Claude Code (CLI) | `~/.config/claude-code/mcp.json` |
| VS Code | `~/.vscode/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Claude Desktop | 视操作系统而定 |

> 欢迎通过 PR 补充更多工具的路径。

---

## 状态保存

连接成功后，Skill 会保存**非敏感状态**到：

```
~/.mcp-orchestrator/state.json
```

内容仅包含服务名、来源路径、最后连接时间，**不包含任何 token、key、密码**。

下次运行时，会先读取此文件，已连接过的服务可直接复用。

---

## 目录结构

```
mcp-game-orchestrator/
├── README.md                  # 本文件
├── SKILL.md                   # 核心 Skill 提示词（复制到 Agent 使用）
├── LICENSE                    # MIT 协议
├── examples/
│   ├── state.example.json     # 状态文件示例
│   └── whitelist.json         # 白名单路径示例（可扩展）
└── scripts/
    └── scan_config.py         # 安全扫描脚本
```

---

## 常见问题

**Q：为什么不能自动下载插件？**
A：MCP 插件本质是可执行进程，自动下载 = 把陌生程序请进你的机器。这是供应链攻击的典型入口。

**Q：为什么授权前不能显示准确权限？**
A：MCP 协议要求先连接才能通过 `tools/list` 获取权限。授权前只能根据配置文件的启动命令做**粗略推断**，Skill 会明确标注"仅为参考"。

**Q：扫描配置文件会不会泄露信息？**
A：不会。Skill 只读取预定义白名单路径，且只提取 MCP 服务名和路径，不读取配置内容，不联网，不上传。

**Q：支持 Windows 吗？**
A：支持。白名单路径中的 `~` 在 Windows 下对应 `%USERPROFILE%`，Agent 会自动解析。

**Q：可以只用来做 MCP 接入，不开发游戏吗？**
A：可以。步骤三是独立的，你可以只走到步骤二，或者在需求收集时说明"仅测试接入"。

---

## 贡献指南

欢迎提交以下类型的 PR：

- 新增 MCP 工具的配置文件白名单路径
- 修正现有路径（工具更新后路径变化）
- 改进提示词的安全逻辑
- 补充其他 Agent 平台的适配说明

**不接受**：
- 任何自动下载/安装相关功能
- 任何绕过用户授权的"便捷"逻辑

---

## 安全免责声明

本项目仅提供**编排逻辑和提示词**，不提供任何 MCP Server 本身。

- 本项目**不对** MCP Server 的安全性负责
- 接入前请**自行确认** MCP 服务来源可信
- 使用本项目造成的任何损失，作者不承担责任

**安全建议**：只接入你自己配置的、来源可信的 MCP Server。

---

## 许可

[MIT License](./LICENSE)

---

## 致谢

灵感来自 MCP 生态中"自动化接入"和"安全边界"之间的张力。