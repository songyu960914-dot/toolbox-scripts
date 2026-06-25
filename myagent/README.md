# MyAgent - OpenClaw Agent Configuration

我的 OpenClaw AI Agent 配置文件模板。

## 文件说明

| 文件 | 用途 |
|------|------|
| `AGENTS.md` | Agent 行为规范（启动流程、记忆管理、群聊规则等） |
| `SOUL.md` | Agent 性格和核心原则 |
| `IDENTITY.md` | Agent 身份信息（名字、形象等） |
| `USER.md` | 用户信息模板 |
| `HEARTBEAT.md` | 定时任务清单 |
| `TOOLS.md` | 工具和环境配置 |
| `MEMORY.md` | 长期记忆模板 |

## 使用方法

将这些文件放到 OpenClaw workspace 目录（`~/.openclaw/workspace/`），Agent 启动时会自动读取。

## 什么是 OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) 是一个开源 AI Agent 框架，让你可以拥有一个持久化的、有记忆的个人 AI 助手。

## 自定义

- 修改 `SOUL.md` 调整 Agent 性格
- 修改 `IDENTITY.md` 设定 Agent 身份
- 修改 `HEARTBEAT.md` 设定定时任务
- `MEMORY.md` 会随使用自动积累

---

_基于实际使用经验整理的配置模板_
