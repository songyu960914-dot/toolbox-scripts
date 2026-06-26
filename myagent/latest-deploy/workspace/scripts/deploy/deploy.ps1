# -*- coding: utf-8 -*-
# ============================================================
# OpenClaw 一键部署脚本 (Windows)
# 在新电脑上运行此脚本，完整恢复你的 AI 助手（含所有记忆和配置）
# ============================================================
# 使用方法：
#   1. 将整个 deploy/ 文件夹拷贝到新电脑
#   2. 以管理员权限运行 PowerShell
#   3. 执行: powershell -ExecutionPolicy Bypass -File deploy.ps1
# ============================================================

param(
    [switch]$SkipNodeInstall,
    [switch]$SkipPythonInstall,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# 颜色输出
function Write-Step($msg) { Write-Host "`n[*] $msg" -ForegroundColor Cyan }
function Write-OK($msg) { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    FAIL: $msg" -ForegroundColor Red }

$DEPLOY_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$OPENCLAW_HOME = "$env:USERPROFILE\.openclaw"
$WORKSPACE = "$OPENCLAW_HOME\workspace"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  OpenClaw Deployment Script" -ForegroundColor Cyan
Write-Host "  Deploy Dir: $DEPLOY_DIR" -ForegroundColor Cyan
Write-Host "  Target:     $OPENCLAW_HOME" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ============================================================
# Step 1: 检查/安装 Node.js
# ============================================================
Write-Step "Checking Node.js..."
$nodeInstalled = $false
try {
    $nodeVersion = node -v 2>$null
    if ($nodeVersion) {
        Write-OK "Node.js $nodeVersion already installed"
        $nodeInstalled = $true
    }
} catch {}

if (-not $nodeInstalled -and -not $SkipNodeInstall) {
    Write-Warn "Node.js not found. Installing via winget..."
    if (-not $DryRun) {
        winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
}

# ============================================================
# Step 2: 检查/安装 Python
# ============================================================
Write-Step "Checking Python..."
$pythonInstalled = $false
try {
    $pyVersion = python --version 2>$null
    if ($pyVersion) {
        Write-OK "Python $pyVersion already installed"
        $pythonInstalled = $true
    }
} catch {}

if (-not $pythonInstalled -and -not $SkipPythonInstall) {
    Write-Warn "Python not found. Installing via winget..."
    if (-not $DryRun) {
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
}

# ============================================================
# Step 3: 安装 Python 依赖
# ============================================================
Write-Step "Installing Python dependencies..."
if (-not $DryRun) {
    pip install --user pandas openpyxl requests openai pyyaml 2>$null
    Write-OK "Python dependencies installed"
}

# ============================================================
# Step 4: 安装 OpenClaw
# ============================================================
Write-Step "Installing OpenClaw..."
try {
    $ocVersion = openclaw --version 2>$null
    if ($ocVersion) {
        Write-OK "OpenClaw already installed: $ocVersion"
    } else { throw "not found" }
} catch {
    if (-not $DryRun) {
        npm install -g openclaw
        Write-OK "OpenClaw installed"
    }
}

# ============================================================
# Step 5: 安装 GitHub CLI
# ============================================================
Write-Step "Checking GitHub CLI..."
try {
    $ghVersion = gh --version 2>$null
    if ($ghVersion) {
        Write-OK "GitHub CLI already installed"
    } else { throw "not found" }
} catch {
    Write-Warn "GitHub CLI not found. Installing..."
    if (-not $DryRun) {
        winget install GitHub.cli --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        Write-OK "GitHub CLI installed"
    }
}

# ============================================================
# Step 6: 部署 OpenClaw 配置
# ============================================================
Write-Step "Deploying OpenClaw configuration..."
if (-not $DryRun) {
    # 创建目录结构
    New-Item -ItemType Directory -Force -Path $OPENCLAW_HOME | Out-Null
    New-Item -ItemType Directory -Force -Path $WORKSPACE | Out-Null
    New-Item -ItemType Directory -Force -Path "$OPENCLAW_HOME\memory" | Out-Null
    New-Item -ItemType Directory -Force -Path "$OPENCLAW_HOME\identity" | Out-Null
    
    # 复制核心配置
    Copy-Item "$DEPLOY_DIR\config\openclaw.json" "$OPENCLAW_HOME\openclaw.json" -Force
    Write-OK "Core config deployed"
}

# ============================================================
# Step 7: 部署 Workspace（记忆 + 灵魂 + 工具）
# ============================================================
Write-Step "Deploying workspace (memory, soul, tools)..."
if (-not $DryRun) {
    $workspaceFiles = @(
        "AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md",
        "TOOLS.md", "MEMORY.md", "HEARTBEAT.md"
    )
    foreach ($file in $workspaceFiles) {
        $src = "$DEPLOY_DIR\workspace\$file"
        if (Test-Path $src) {
            Copy-Item $src "$WORKSPACE\$file" -Force
            Write-OK "  $file"
        }
    }
    
    # 复制 daily-logs
    if (Test-Path "$DEPLOY_DIR\workspace\daily-logs") {
        Copy-Item "$DEPLOY_DIR\workspace\daily-logs" "$WORKSPACE\daily-logs" -Recurse -Force
        Write-OK "  daily-logs/"
    }
    
    # 复制 scripts
    if (Test-Path "$DEPLOY_DIR\workspace\scripts") {
        Copy-Item "$DEPLOY_DIR\workspace\scripts" "$WORKSPACE\scripts" -Recurse -Force
        Write-OK "  scripts/"
    }
    
    # 复制工具脚本
    if (Test-Path "$DEPLOY_DIR\workspace\huggingface-dataset-extractor") {
        Copy-Item "$DEPLOY_DIR\workspace\huggingface-dataset-extractor" "$WORKSPACE\huggingface-dataset-extractor" -Recurse -Force
        Write-OK "  huggingface-dataset-extractor/"
    }
}

# ============================================================
# Step 8: 配置 Git 代理（中国网络）
# ============================================================
Write-Step "Configuring Git proxy..."
if (-not $DryRun) {
    Write-Warn "If you use Clash or similar proxy on port 7890, configure with:"
    Write-Host "    git config --global http.proxy http://127.0.0.1:7890"
    Write-Host "    git config --global https.proxy http://127.0.0.1:7890"
}

# ============================================================
# Step 9: 提示手动步骤
# ============================================================
Write-Step "Manual steps required:"
Write-Host ""
Write-Host "  1. 配置 LiteLLM (如果使用本地代理):" -ForegroundColor Yellow
Write-Host "     编辑 $OPENCLAW_HOME\openclaw.json"
Write-Host "     修改 models.providers.litellm.baseUrl 和 apiKey"
Write-Host ""
Write-Host "  2. GitHub 认证:" -ForegroundColor Yellow
Write-Host "     gh auth login"
Write-Host ""
Write-Host "  3. 智谱 API Key:" -ForegroundColor Yellow
Write-Host "     编辑 $WORKSPACE\huggingface-dataset-extractor\*\config.yaml"
Write-Host "     将 api_key 改为你的真实 Key"
Write-Host ""
Write-Host "  4. 启动 OpenClaw:" -ForegroundColor Yellow
Write-Host "     openclaw start"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "  Your AI assistant is ready. All memories preserved." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
