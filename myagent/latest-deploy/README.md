# OpenClaw 部署包（自动生成）

**生成时间：** 2026-06-26 17:01:06

## ⚠️ 安装后请修改以下配置

1. **`config/openclaw.json`**
   - `models.providers.litellm.apiKey` → 改为你的 LiteLLM API Key
   - `gateway.auth.token` → 改为新的 gateway token（或保持默认）

2. **`workspace/huggingface-dataset-extractor/*/config.yaml`**
   - `llm.api_key` → 改为你的智谱 API Key

3. **GitHub 认证**
   ```bash
   gh auth login
   gh auth setup-git
   ```

4. **Git 代理（中国网络）**
   ```bash
   git config --global http.proxy http://127.0.0.1:7890
   git config --global https.proxy http://127.0.0.1:7890
   ```

## 部署步骤

```powershell
# Windows - 以管理员身份运行 PowerShell
powershell -ExecutionPolicy Bypass -File workspace/scripts/deploy/deploy.ps1
```

## 文件清单

```
latest-deploy/
├── config/
│   └── openclaw.json           # OpenClaw 核心配置（已脱敏）
├── workspace/
│   ├── AGENTS.md               # 行为规范
│   ├── SOUL.md                 # 个性
│   ├── IDENTITY.md             # 身份
│   ├── USER.md                 # 用户信息
│   ├── MEMORY.md               # 长期记忆
│   ├── TOOLS.md                # 工具配置
│   ├── HEARTBEAT.md            # 定期任务
│   ├── daily-logs/             # 工作日志（近30天）
│   ├── scripts/                # 工具脚本
│   └── huggingface-dataset-extractor/
└── README.md                   # 本文件
```
