# -*- mode: pwsh -*-
# ZUA-2026 Demo 一键启动脚本
# 用法：在【你自己的终端】（有网的终端，不是受限会话）里执行：
#   cd demo
#   powershell -ExecutionPolicy Bypass -File setup.ps1
# 或右键 -> 使用 PowerShell 运行

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ---- 1. 确保有真实 Python ----
function Get-PyCmd {
    # 返回 @(命令, 参数...)；找不到返回 $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try { $null = & python --version 2>$null; if ($LASTEXITCODE -eq 0) { return @("python") } } catch {}
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in @("3.12", "3.11", "3.10")) {
            try { $null = & py -$v --version 2>$null; if ($LASTEXITCODE -eq 0) { return @("py", "-$v") } } catch {}
        }
    }
    return $null
}

$pyCmd = Get-PyCmd
if (-not $pyCmd) {
    Write-Host @"

[!] 未找到可用的 Python。
    这台机器只装了 Python 管理器（py），请先在终端运行一次：
        py install 3.12
    或从 https://www.python.org/downloads/ 下载官方安装包，勾选 "Add python.exe to PATH" 安装。
    然后重新运行本脚本。
"@
    exit 1
}
Write-Host "[1/3] 使用 Python: $($pyCmd -join ' ')"

# ---- 2. 创建虚拟环境 ----
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[2/3] 创建虚拟环境 .venv ..."
    & $pyCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host "venv 创建失败"; exit 1 }
}
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

# ---- 3. 安装依赖（国内用清华源加速）----
Write-Host "[3/3] 安装依赖（清华 PyPI 镜像）..."
& $venvPy -m pip install --upgrade pip -q -i https://pypi.tuna.tsinghua.edu.cn/simple
& $venvPy -m pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple
if ($LASTEXITCODE -ne 0) {
    Write-Host "依赖安装失败：若网络需要代理，请先启动你的代理软件（系统代理会被 pip 自动读取）后重试。"
    exit 1
}

# ---- 4. 启动 ----
Write-Host ""
Write-Host "======================================================"
Write-Host "  启动成功！"
Write-Host "  本机测试：   http://127.0.0.1:8000"
Write-Host "  局域网测试： http://<本机IP>:8000   （防火墙需放行 8000）"
Write-Host "  按 Ctrl+C 停止"
Write-Host "======================================================"
& $venvPy -m uvicorn main:app --host 0.0.0.0 --port 8000
