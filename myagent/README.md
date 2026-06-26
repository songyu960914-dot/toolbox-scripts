# MyAgent - OpenClaw AI Assistant Configuration Template

一键部署你的个人 AI 助手，包含完整记忆、灵魂、工具脚本。

---

## 📦 这是什么？

这是一个完整的 OpenClaw AI 助手配置模板 + 部署工具包。克隆到新电脑后，运行一个脚本就能完整复现你的 AI 助手，包括：

- ✅ 所有记忆（长期记忆 + 工作日志）
- ✅ 个性和行为规范
- ✅ 工作脚本和工具
- ✅ 自动安装所有依赖

---

## 🚀 快速开始

### 选项 1：从头开始配置（新用户）

如果你是第一次使用 OpenClaw：

```bash
# 1. 克隆仓库
git clone https://github.com/songyu960914-dot/toolbox-scripts.git
cd toolbox-scripts/myagent

# 2. 复制配置模板到 OpenClaw workspace
cp -r config-template/* ~/.openclaw/workspace/

# 3. 安装 OpenClaw
npm install -g openclaw

# 4. 启动
openclaw start
```

### 选项 2：迁移到新电脑（已有配置）

如果你已经在用 OpenClaw，想迁移到新电脑：

#### 步骤 A：在旧电脑打包

```bash
cd ~/.openclaw/workspace/scripts
python package_deploy.py
```

会在桌面生成 `openclaw-deploy-YYYYMMDD.zip`。

#### 步骤 B：在新电脑部署

1. 将 zip 文件拷贝到新电脑
2. 解压到任意位置
3. **以管理员身份**运行 PowerShell
4. 执行：

```powershell
cd 解压路径/openclaw-deploy-YYYYMMDD
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

脚本会自动：
- ✅ 检查/安装 Node.js, Python, GitHub CLI
- ✅ 安装 OpenClaw 和所有依赖
- ✅ 部署你的配置和记忆
- ✅ 恢复所有工作脚本

---

## 📂 目录结构

```
myagent/
├── README.md                    ← 本文件
├── 使用指南.md                  ← 详细使用说明
├── config-template/             ← 配置模板（新用户）
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── USER.md
│   ├── MEMORY.md
│   ├── TOOLS.md
│   └── HEARTBEAT.md
├── scripts/                     ← 部署和工具脚本
│   ├── package_deploy.py        ← 打包脚本
│   ├── deploy.ps1               ← Windows 自动部署
│   └── safe_delete.py           ← 安全删除工具
└── tools/                       ← 可选工具集
    └── huggingface-extractor/   ← HF 数据集提取
```

---

## 📖 文件说明

### 核心配置文件（在 `~/.openclaw/workspace/`）

| 文件 | 用途 |
|------|------|
| `AGENTS.md` | 行为规范、红线、工作流程 |
| `SOUL.md` | 个性、语气、价值观 |
| `IDENTITY.md` | 名字、形象、emoji |
| `USER.md` | 用户信息（你是谁） |
| `MEMORY.md` | 长期记忆（重要决定、偏好、经验教训） |
| `TOOLS.md` | 工具配置（相机名称、API Key 位置等） |
| `HEARTBEAT.md` | 定期任务（清理、检查等） |
| `daily-logs/YYYY-MM-DD.md` | 每日工作日志 |

### 工具脚本（在 `~/.openclaw/workspace/scripts/`）

| 脚本 | 功能 |
|------|------|
| `safe_delete.py` | 安全删除（文件进中转站保留3天，压缩存储） |
| `package_deploy.py` | 打包当前配置为部署包 |

---

## 🔧 手动配置项

部署脚本运行后，还需要手动配置：

### 1. GitHub 认证

```bash
gh auth login
```

选择：
- GitHub.com
- HTTPS
- Yes (authenticate Git)
- Login with a web browser

### 2. LiteLLM 配置（如果使用本地代理）

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "models": {
    "providers": {
      "litellm": {
        "baseUrl": "http://127.0.0.1:4000",
        "apiKey": "your-key-here"
      }
    }
  }
}
```

### 3. API Keys

如果使用 HuggingFace 提取工具，编辑：
```
~/.openclaw/workspace/huggingface-dataset-extractor/*/config.yaml
```

将 `${ZHIPU_API_KEY}` 改为真实 Key。

### 4. Git 代理（中国网络）

如果使用 Clash 等代理（默认 7890 端口）：

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

---

## 🛠️ 常用命令

```bash
# 启动 OpenClaw
openclaw start

# 停止 OpenClaw
openclaw stop

# 重启 OpenClaw
openclaw restart

# 查看状态
openclaw status

# 查看日志
tail -f ~/.openclaw/logs/gateway.log

# 安全删除文件
python scripts/safe_delete.py delete <path>

# 列出中转站内容
python scripts/safe_delete.py list

# 还原文件
python scripts/safe_delete.py restore <文件名.zip>

# 打包当前配置（迁移到新电脑前）
python scripts/package_deploy.py
```

---

## 📝 定制你的助手

### 修改个性

编辑 `~/.openclaw/workspace/SOUL.md`，调整：
- 语气风格
- 价值观
- 边界红线

### 添加工具

1. 在 `~/.openclaw/workspace/scripts/` 放置新脚本
2. 在 `TOOLS.md` 中记录使用方法
3. 重启 OpenClaw

### 添加记忆

长期记忆写入 `MEMORY.md`，短期记录自动进入 `daily-logs/`。

---

## 🔐 安全注意事项

1. **API Keys 不在仓库中**
   - `openclaw.json` 中的 API Key 需要手动配置
   - 工具脚本的 config.yaml 使用占位符

2. **记忆数据含隐私**
   - `MEMORY.md` 和 `daily-logs/` 包含你的工作记录
   - 部署包包含完整记忆，请妥善保管

3. **GitHub 凭据不迁移**
   - 新电脑需要重新 `gh auth login`

---

## 🐛 故障排查

### OpenClaw 启动失败

```bash
# 检查端口占用
netstat -ano | findstr 18789  # Windows
lsof -i :18789                # macOS/Linux

# 查看日志
cat ~/.openclaw/logs/gateway.log
```

### Python 依赖问题

```bash
# 重新安装依赖
pip install -r requirements.txt
```

### 部署脚本失败

- 确保以管理员身份运行
- 手动安装 Node.js: https://nodejs.org/
- 手动安装 Python: https://www.python.org/

---

## 📄 许可

MIT License

---

## 🤝 贡献

欢迎 PR！如果你有好的配置技巧或工具脚本，欢迎提交。

---

## 📞 支持

- OpenClaw 文档: https://docs.openclaw.ai
- OpenClaw Discord: https://discord.com/invite/clawd
- Issues: https://github.com/songyu960914-dot/toolbox-scripts/issues

---

**享受你的个人 AI 助手！** 🚀
