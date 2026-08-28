# ZUA-2026 一键清库脚本（上线前清理测试残留用）
# 功能：自动备份当前数据库到 data\backup\，然后清空玩家/通关/浏览/提示记录
# 注意：运行前请先停止服务进程（start-local.bat / start-prod.bat），否则数据库可能被占用
# 用法：.\reset_db.ps1
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ZUA-2026 一键清库" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$dbPath = Join-Path $PSScriptRoot "data\puzzle.db"
if (-not (Test-Path -LiteralPath $dbPath)) {
    Write-Host "未找到数据库文件：$dbPath（无需清理）" -ForegroundColor Yellow
    exit 0
}

# 1. 备份（保留现场，误操作可回滚）
$backupDir = Join-Path $PSScriptRoot "data\backup"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $backupDir "pre-reset-$ts.db"
Copy-Item -LiteralPath $dbPath -Destination $backupPath
Write-Host "[1/2] 已备份数据库 -> $backupPath" -ForegroundColor Green

# 2. 清空业务表（保留表结构；如需彻底重建可直接删除整个 data 目录）
#    注意：下面 Python 代码里一律用单引号——Windows PowerShell 5.1 把字符串传给
#    外部程序时会吞掉内嵌双引号（旧版 r"$dbPath" 被拆成 rC:\... 导致 SyntaxError）。
$py = @"
import sqlite3
conn = sqlite3.connect(r'$dbPath')
cur = conn.cursor()
for table in ('solves', 'level_views', 'players', 'hints_revealed'):
    n = cur.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
    cur.execute('DELETE FROM ' + table)
    print('  cleared ' + table + ': ' + str(n) + ' rows')
conn.commit()
conn.execute('VACUUM')
conn.close()
print('database cleared')
"@
# 优先用项目自带的 venv Python（必定存在），否则退回系统 python
$pyExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pyExe)) { $pyExe = "python" }
& $pyExe -X utf8 -c $py
if ($LASTEXITCODE -ne 0) {
    Write-Host "清空失败：请确认已停止服务进程后重试" -ForegroundColor Red
    exit 1
}
Write-Host "[2/2] 完成。排行榜与会话记录已全部清除。" -ForegroundColor Green
