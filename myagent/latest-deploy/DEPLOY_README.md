# 部署包

**打包时间**: 2026-06-30 17:32

## 包含内容

- workspace 核心 md 文件（AGENTS.md、SOUL.md、TOOLS.md、MEMORY.md 等）
- scripts/ 目录（auto_package_push.py、safe_delete.py）
- memory/ 目录（日志文件）

## 新电脑部署步骤

1. 解压 `workspace_deploy_20260630.zip` 到 OpenClaw workspace 目录（`~/.openclaw/workspace/`）
2. 替换 OpenClaw `config/openclaw.json` 中的 apiKey 和 gateway token
3. 替换 HuggingFace 工具的 config.yaml 中的智谱 Key（如需要）
4. 运行 `gh auth login` 配置 GitHub 认证
5. 配置 Git 代理（如需要）

## 脱敏说明

所有敏感信息已替换为占位符：
- 智谱 API Key → `${ZHIPU_API_KEY}`
- LiteLLM API Key → `${API_KEY}`
- GitHub Token → `${GITHUB_TOKEN}`
- Gateway Token → `${GATEWAY_TOKEN}`
