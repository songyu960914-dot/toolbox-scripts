# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## HuggingFace 数据集批量提取

**触发词：**"跑一下 HuggingFace 数据集"、"抓取 HF 数据集元信息"、"工作簿跑一下"

**脚本位置：** `workspace/huggingface-dataset-extractor/`
- v1: 原版串行
- v2: 合并LLM + 配置外部化
- v3: 并发版

**智谱 API:**
- Base URL: https://open.bigmodel.cn/api/paas/v4
- Model: glm-5-turbo
- Key: 存储在各版本 config.yaml 中（本地），GitHub 上用 ${ZHIPU_API_KEY} 占位

**GitHub 仓库:** https://github.com/songyu960914-dot/toolbox-scripts

**执行（推荐 v2 串行版）：**
```bash
cd toolbox-scripts/huggingface-dataset-extractor/huggingface-dataset-extractor_v2
python run_workbook.py 工作簿1
```

## temp/ 临时文件夹

调试脚本、测试 API、临时生成的中间文件都放这里。

**规则：**
- 所有临时/测试文件写到 `temp/` 而非 workspace 根目录
- 超过 3 天的文件自动清理（通过 heartbeat 检查）
- 不纳入迁移/备份

## 中转站（trash/）

安全删除机制：文件先移到中转站保留3天，压缩存储节省空间。

**使用方法：**
```bash
# 删除文件/目录（移到中转站）
python scripts/safe_delete.py delete <path> [原因]

# 列出中转站内容
python scripts/safe_delete.py list

# 还原文件
python scripts/safe_delete.py restore <压缩包名> [目标路径]

# 手动清理（超过3天的）
python scripts/safe_delete.py cleanup [天数]
```

**压缩率：** 一般文本文件可节省 60-80% 空间。

**自动清理：** heartbeat 每天检查一次，自动清理超过3天的文件。

## 自动部署包推送

**脚本：** `scripts/auto_package_push.py`

**运行方式：** Cron 每天 17:00 自动执行（ID: `b8729b5d-86e0-4592-92ac-c0d5b4e32772`）

**功能：**
- 打包 workspace 配置和记忆文件
- 脱敏处理（API Key 替换为环境变量占位符）
- 推送到 GitHub: `toolbox-scripts/myagent/latest-deploy/`

**脱敏规则：**
- 智谱 API Key → `${ZHIPU_API_KEY}`
- LiteLLM API Key → `${API_KEY}`
- GitHub Token → `${GITHUB_TOKEN}`
- Gateway Token → `${GATEWAY_TOKEN}`

**新电脑部署后手动配置：**
1. 替换 `config/openclaw.json` 中的 apiKey 和 gateway token
2. 替换 HuggingFace 工具的 config.yaml 中的智谱 Key
3. 运行 `gh auth login` 配置 GitHub 认证
4. 配置 Git 代理（如需要）

---

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
