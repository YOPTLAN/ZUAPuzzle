# -*- mode: pwsh -*-
# ZUA-2026 Demo 一键安装脚本（只装环境，不负责启动；启动请用 start-local.bat / start-prod.bat）
# 用法：在【你自己的终端】（有网的终端，不是受限会话）里执行：
#   cd demo
#   powershell -ExecutionPolicy Bypass -File setup.ps1
# 或右键 -> 使用 PowerShell 运行

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ---- 读取配置（Python 模块）----
$cfg = & python -c "import sys; sys.path.insert(0, '.'); from config import config; print('PIP_INDEX_URL=' + config.PIP_INDEX_URL)" 2>$null
if ($LASTEXITCODE -ne 0) {
    $PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
} else {
    $PIP_INDEX_URL = ($cfg | Select-String 'PIP_INDEX_URL=(.+)').Matches.Groups[1].Value
}

# ---- 1. 确保有真实 Python（动态检测，不预设版本）----
# 返回 @{ Exe = "python"; Args = @() } 或 @{ Exe = "py"; Args = @("-3.14") }；找不到返回 $null
function Get-PyCmd {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try { $null = & python --version 2>$null; if ($LASTEXITCODE -eq 0) { return @{ Exe = "python"; Args = @() } } } catch {}
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $versions = & py -0 2>&1 | Select-String '^\s*-V:(\d+\.\d+)' | ForEach-Object { $_.Matches.Groups[1].Value } | Sort-Object -Descending
        foreach ($v in $versions) { try { $null = & py -$v --version 2>$null; if ($LASTEXITCODE -eq 0) { return @{ Exe = "py"; Args = @("-$v") } } } catch {} }
    }
    foreach ($v in @("3.12", "3.11", "3.10")) { try { $null = & py -$v --version 2>$null; if ($LASTEXITCODE -eq 0) { return @{ Exe = "py"; Args = @("-$v") } } } catch {} }
    return $null
}

$pyCmd = Get-PyCmd
if (-not $pyCmd) {
    Write-Host "[!] 未找到可用的 Python。"
    Write-Host "    请先安装 Python："
    Write-Host '    - 从 https://www.python.org/downloads/ 下载官方安装包，勾选 "Add python.exe to PATH"'
    Write-Host "    - 或用包管理器：winget install Python.Python.3.12 / scoop install python"
    Write-Host "    然后重新运行本脚本。"
    exit 1
}
$pyArgs = @($pyCmd.Args)
Write-Host "[1/3] 使用 Python: $($pyCmd.Exe) $($pyArgs -join ' ')".TrimEnd()

# ---- 2. 创建/校验虚拟环境 ----
# venv 里的 python.exe 只是启动器，会按 pyvenv.cfg 寻找真实 Python。
# 若 home 路径已失效（换机/改名/卸载），启动器报 "No Python at ..."，
# 因此不能只看文件存在，必须实际运行一次验证。
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvValid = $false
if (Test-Path $venvPy) {
    try {
        $null = & $venvPy --version 2>$null
        if ($LASTEXITCODE -eq 0) { $venvValid = $true }
    } catch {}
}

if (-not $venvValid) {
    if (Test-Path ".venv") {
        # 损坏的 venv 不直接删除，移入待删文件夹由用户自行清理
        $trashDir = Join-Path ([System.IO.Path]::GetTempPath()) "ZUAPuzzle_trash\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        New-Item -ItemType Directory -Path $trashDir -Force | Out-Null
        try {
            Move-Item -Path ".venv" -Destination (Join-Path $trashDir ".venv") -Force
            Write-Host "[2/3] 检测到无效的虚拟环境（Python 路径失效），旧目录已移至:"
            Write-Host "      $trashDir\.venv （可自行删除）"
        } catch {
            Write-Host "[!] 旧 .venv 移除失败：$($_.Exception.Message)"
            exit 1
        }
    }
    Write-Host "[2/3] 创建虚拟环境 .venv ..."
    & $pyCmd.Exe @pyArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host "venv 创建失败"; exit 1 }
}

# ---- 3. 安装依赖（可配置镜像源 + 不可用时自动回退官方源）----
function Test-PipIndex {
    param([string]$url)
    try {
        $probe = $url.TrimEnd('/') + '/pip/'
        $resp = Invoke-WebRequest -Uri $probe -Method Head -TimeoutSec 8 -UseBasicParsing
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
    } catch { return $false }
}

Write-Host "[3/3] 安装依赖（镜像源: $PIP_INDEX_URL）..."
if (-not (Test-PipIndex $PIP_INDEX_URL)) {
    Write-Host "[!] 镜像源不可用（超时或被拒），自动回退到官方 PyPI ..."
    $PIP_INDEX_URL = "https://pypi.org/simple"
}
& "$venvPy" -m pip install --upgrade pip -q -i $PIP_INDEX_URL
& "$venvPy" -m pip install -r requirements.txt -q -i $PIP_INDEX_URL
if ($LASTEXITCODE -ne 0) {
    Write-Host "依赖安装失败：若网络需要代理，请先启动你的代理软件（系统代理会被 pip 自动读取）后重试。"
    exit 1
}

# ---- 4. 完成（启动职责已移交 start-local.bat / start-prod.bat）----
Write-Host ""
Write-Host "======================================================"
Write-Host "  ✅ 安装完成！环境就绪：.venv + 依赖"
Write-Host "  本地/局域网测试 : .\start-local.bat   （Cookie Secure 关）"
Write-Host "  对外/内网穿透   : .\start-prod.bat    （Cookie Secure 开）"
Write-Host "======================================================"