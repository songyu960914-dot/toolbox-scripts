# -*- coding: utf-8 -*-
"""
自动打包部署文件并推送到 GitHub（脱敏版）
用于 cron 自动执行，每周生成一次部署包。
"""
import os
import sys
import re
import shutil
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
OPENCLAW_HOME = Path.home() / '.openclaw'
TOOLBOX_REPO = WORKSPACE / 'toolbox-scripts'
DEPLOY_TARGET = TOOLBOX_REPO / 'myagent' / 'latest-deploy'

# 需要脱敏的 Key 模式
SENSITIVE_PATTERNS = [
    # 智谱 API Key 格式
    (r'[a-f0-9]{32}\.[A-Za-z0-9]{12,}', '${ZHIPU_API_KEY}'),
    # 通用 API Key 格式 (sk-xxx, gho_xxx 等)
    (r'sk-[A-Za-z0-9]{20,}', '${API_KEY}'),
    (r'gho_[A-Za-z0-9]{36}', '${GITHUB_TOKEN}'),
    # OpenClaw gateway token
    (r'[a-f0-9]{48}', '${GATEWAY_TOKEN}'),
]

# 不应该出现在公开仓库的文件
SKIP_FILES = [
    'openclaw.json.bak',
    'exec-approvals.json',
    'device.json',
    'device-auth.json',
]


def sanitize_content(content, filename=''):
    """脱敏文件内容"""
    for pattern, replacement in SENSITIVE_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content


def sanitize_json_config(content):
    """特殊处理 openclaw.json - 保留结构但脱敏敏感值"""
    import json
    try:
        config = json.loads(content)
        
        # 脱敏 auth token
        if 'gateway' in config and 'auth' in config['gateway']:
            if 'token' in config['gateway']['auth']:
                config['gateway']['auth']['token'] = '${GATEWAY_TOKEN}'
        
        # 脱敏 API keys
        if 'models' in config and 'providers' in config['models']:
            for provider, pconfig in config['models']['providers'].items():
                if 'apiKey' in pconfig:
                    pconfig['apiKey'] = '${API_KEY}'
        
        return json.dumps(config, indent=2, ensure_ascii=False)
    except:
        return sanitize_content(content)


def package_deploy():
    """打包部署文件（脱敏版）"""
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M")}] 开始打包部署文件（脱敏版）...')
    
    # 清理旧的部署目录
    if DEPLOY_TARGET.exists():
        shutil.rmtree(DEPLOY_TARGET)
    
    DEPLOY_TARGET.mkdir(parents=True)
    (DEPLOY_TARGET / 'config').mkdir()
    (DEPLOY_TARGET / 'workspace').mkdir()
    (DEPLOY_TARGET / 'workspace' / 'daily-logs').mkdir()
    (DEPLOY_TARGET / 'workspace' / 'scripts').mkdir()
    
    # === 1. 复制并脱敏 openclaw.json ===
    config_file = OPENCLAW_HOME / 'openclaw.json'
    if config_file.exists():
        content = config_file.read_text(encoding='utf-8')
        sanitized = sanitize_json_config(content)
        (DEPLOY_TARGET / 'config' / 'openclaw.json').write_text(sanitized, encoding='utf-8')
        print('  ✓ openclaw.json (sanitized)')
    
    # === 2. 复制 workspace 核心文件 ===
    core_files = ['AGENTS.md', 'SOUL.md', 'IDENTITY.md', 'USER.md',
                  'TOOLS.md', 'MEMORY.md', 'HEARTBEAT.md']
    
    for file in core_files:
        src = WORKSPACE / file
        if src.exists():
            content = src.read_text(encoding='utf-8')
            sanitized = sanitize_content(content, file)
            (DEPLOY_TARGET / 'workspace' / file).write_text(sanitized, encoding='utf-8')
            print(f'  ✓ {file}')
    
    # === 3. 复制 daily-logs（近30天）===
    daily_logs_src = WORKSPACE / 'daily-logs'
    if daily_logs_src.exists():
        cutoff = datetime.now() - timedelta(days=30)
        count = 0
        for log_file in daily_logs_src.glob('*.md'):
            if log_file.name == 'README.md':
                shutil.copy(log_file, DEPLOY_TARGET / 'workspace' / 'daily-logs' / log_file.name)
                continue
            try:
                file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                if file_date >= cutoff:
                    content = log_file.read_text(encoding='utf-8')
                    sanitized = sanitize_content(content, log_file.name)
                    (DEPLOY_TARGET / 'workspace' / 'daily-logs' / log_file.name).write_text(
                        sanitized, encoding='utf-8')
                    count += 1
            except:
                pass
        print(f'  ✓ daily-logs ({count} files)')
    
    # === 4. 复制 scripts ===
    scripts_src = WORKSPACE / 'scripts'
    if scripts_src.exists():
        for script_file in scripts_src.rglob('*'):
            if script_file.is_file() and '__pycache__' not in str(script_file):
                rel_path = script_file.relative_to(scripts_src)
                dest = DEPLOY_TARGET / 'workspace' / 'scripts' / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if script_file.suffix in ['.py', '.ps1', '.yaml', '.yml', '.json']:
                    content = script_file.read_text(encoding='utf-8')
                    sanitized = sanitize_content(content, script_file.name)
                    dest.write_text(sanitized, encoding='utf-8')
                else:
                    shutil.copy(script_file, dest)
        print('  ✓ scripts/')
    
    # === 5. 复制 huggingface-dataset-extractor ===
    hf_src = WORKSPACE / 'huggingface-dataset-extractor'
    if hf_src.exists():
        hf_dst = DEPLOY_TARGET / 'workspace' / 'huggingface-dataset-extractor'
        hf_dst.mkdir(parents=True)
        
        for item in hf_src.rglob('*'):
            if item.is_file() and '__pycache__' not in str(item) and '.git' not in str(item):
                rel_path = item.relative_to(hf_src)
                dest = hf_dst / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if item.suffix in ['.py', '.yaml', '.yml', '.json', '.md']:
                    try:
                        content = item.read_text(encoding='utf-8')
                        sanitized = sanitize_content(content, item.name)
                        dest.write_text(sanitized, encoding='utf-8')
                    except:
                        shutil.copy(item, dest)
                else:
                    shutil.copy(item, dest)
        print('  ✓ huggingface-dataset-extractor/')
    
    # === 6. 生成部署说明 ===
    deploy_readme = f"""# OpenClaw 部署包（自动生成）

**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
"""
    (DEPLOY_TARGET / 'README.md').write_text(deploy_readme, encoding='utf-8')
    print('  ✓ README.md')
    
    return True


def git_push():
    """提交并推送到 GitHub"""
    os.chdir(TOOLBOX_REPO)
    
    # 检查是否有变更
    result = subprocess.run(['git', 'add', 'myagent/latest-deploy/'],
                          capture_output=True, text=True)
    
    result = subprocess.run(['git', 'status', '--porcelain'],
                          capture_output=True, text=True)
    
    if not result.stdout.strip():
        print('  没有变更，跳过推送')
        return True
    
    # 提交
    msg = f'auto: weekly deploy package update ({datetime.now().strftime("%Y-%m-%d")})'
    subprocess.run(['git', 'commit', '-m', msg], capture_output=True, text=True)
    
    # 推送
    result = subprocess.run(['git', 'push'], capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        print('  ✓ 已推送到 GitHub')
        return True
    else:
        print(f'  ✗ 推送失败: {result.stderr}')
        return False


if __name__ == '__main__':
    success = package_deploy()
    if success:
        print('\n推送到 GitHub...')
        git_push()
        print('\n完成！')
