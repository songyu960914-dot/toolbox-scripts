# -*- coding: utf-8 -*-
"""
打包脚本：生成可移植的部署包
运行后会在桌面生成 openclaw-deploy.zip
"""
import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
DESKTOP = Path.home() / 'Desktop'
DEPLOY_NAME = f'openclaw-deploy-{datetime.now().strftime("%Y%m%d")}'
DEPLOY_DIR = DESKTOP / DEPLOY_NAME

print(f'正在打包部署文件...')
print(f'源: {WORKSPACE}')
print(f'目标: {DEPLOY_DIR}')

# 清理旧的部署目录
if DEPLOY_DIR.exists():
    shutil.rmtree(DEPLOY_DIR)

# 创建部署目录结构
(DEPLOY_DIR / 'config').mkdir(parents=True)
(DEPLOY_DIR / 'workspace').mkdir(parents=True)

# ============================================================
# 1. 复制 OpenClaw 配置
# ============================================================
print('\n[1/5] 复制 OpenClaw 配置...')
openclaw_home = Path.home() / '.openclaw'
config_file = openclaw_home / 'openclaw.json'

if config_file.exists():
    shutil.copy(config_file, DEPLOY_DIR / 'config' / 'openclaw.json')
    print('  ✓ openclaw.json')
else:
    print('  ⚠ openclaw.json 不存在，需要手动配置')

# ============================================================
# 2. 复制 Workspace 核心文件
# ============================================================
print('\n[2/5] 复制 Workspace 核心文件...')
core_files = [
    'AGENTS.md', 'SOUL.md', 'IDENTITY.md', 'USER.md',
    'TOOLS.md', 'MEMORY.md', 'HEARTBEAT.md'
]

for file in core_files:
    src = WORKSPACE / file
    if src.exists():
        shutil.copy(src, DEPLOY_DIR / 'workspace' / file)
        print(f'  ✓ {file}')
    else:
        print(f'  ⚠ {file} 不存在')

# ============================================================
# 3. 复制 daily-logs（近30天）
# ============================================================
print('\n[3/5] 复制 daily-logs（近30天）...')
daily_logs_src = WORKSPACE / 'daily-logs'
if daily_logs_src.exists():
    daily_logs_dst = DEPLOY_DIR / 'workspace' / 'daily-logs'
    daily_logs_dst.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=30)
    
    copied_count = 0
    for log_file in daily_logs_src.glob('*.md'):
        if log_file.name == 'README.md':
            shutil.copy(log_file, daily_logs_dst / log_file.name)
            continue
        
        # 解析日期
        try:
            file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
            if file_date >= cutoff:
                shutil.copy(log_file, daily_logs_dst / log_file.name)
                copied_count += 1
        except:
            pass
    
    print(f'  ✓ {copied_count} 个日志文件')
else:
    print('  ⚠ daily-logs 不存在')

# ============================================================
# 4. 复制 scripts/
# ============================================================
print('\n[4/5] 复制 scripts...')
scripts_src = WORKSPACE / 'scripts'
if scripts_src.exists():
    scripts_dst = DEPLOY_DIR / 'workspace' / 'scripts'
    shutil.copytree(scripts_src, scripts_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    print(f'  ✓ scripts/')

# ============================================================
# 5. 复制工具脚本（HuggingFace 等）
# ============================================================
print('\n[5/5] 复制工具脚本...')
hf_src = WORKSPACE / 'huggingface-dataset-extractor'
if hf_src.exists():
    hf_dst = DEPLOY_DIR / 'workspace' / 'huggingface-dataset-extractor'
    shutil.copytree(
        hf_src, hf_dst,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git')
    )
    print(f'  ✓ huggingface-dataset-extractor/')

# ============================================================
# 6. 生成 README
# ============================================================
print('\n生成 README...')
readme_content = """# OpenClaw 部署包

此部署包包含：
- OpenClaw 配置（openclaw.json）
- AI 助手的记忆和灵魂（AGENTS.md, SOUL.md, MEMORY.md 等）
- 工作脚本（safe_delete, HuggingFace 提取工具等）
- 近30天工作日志

## 安装步骤

1. 确保你有管理员权限
2. 以管理员身份运行 PowerShell
3. 执行：
   ```powershell
   powershell -ExecutionPolicy Bypass -File deploy.ps1
   ```

4. 按提示完成手动配置步骤

## 手动配置项

- **LiteLLM:** 如使用本地代理，编辑 `config/openclaw.json` 中的 baseUrl 和 apiKey
- **GitHub:** 运行 `gh auth login` 登录你的 GitHub 账号
- **智谱 API Key:** 编辑工具脚本中的 config.yaml，填入真实 API Key

## 启动

```bash
openclaw start
```

---

打包时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

with open(DEPLOY_DIR / 'README.md', 'w', encoding='utf-8') as f:
    f.write(readme_content)
print('  ✓ README.md')

# ============================================================
# 7. 生成 requirements.txt
# ============================================================
print('\n生成 requirements.txt...')
requirements = """pandas>=2.0.0
openpyxl>=3.0.0
requests>=2.30.0
openai>=1.0.0
pyyaml>=6.0.0
"""

with open(DEPLOY_DIR / 'requirements.txt', 'w', encoding='utf-8') as f:
    f.write(requirements)
print('  ✓ requirements.txt')

# ============================================================
# 8. 压缩打包
# ============================================================
print('\n压缩打包...')
zip_path = DESKTOP / f'{DEPLOY_NAME}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(DEPLOY_DIR):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(DEPLOY_DIR.parent)
            zf.write(file_path, arcname)

# 计算大小
zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

print('\n============================================================')
print(f'打包完成！')
print(f'文件: {zip_path}')
print(f'大小: {zip_size_mb:.2f} MB')
print('============================================================')
print('\n将此 ZIP 文件拷贝到新电脑，解压后运行 deploy.ps1 即可完整恢复。')
