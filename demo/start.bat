@echo off
cd /d "%~dp0"

:: Read port from config.py (delims= takes the whole line; output is a bare value)
for /f "delims=" %%a in ('python -c "import sys; sys.path.insert(0, '.'); from config import config; print(int(config.PORT))" 2^>nul') do set PORT=%%a
if not defined PORT set PORT=8000

:: Auto-detect LAN IPv4 (non-loopback, exclude APIPA 169.254.x). Note: $ needs NO escaping in .bat
for /f "delims=" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } | Select-Object -First 1).IPAddress" 2^>nul') do set LAN_IP=%%a
if not defined LAN_IP set LAN_IP=[detect-failed]

echo ============================================
echo   ZUA-2026 BlackBox Server
echo   Local   : http://127.0.0.1:%PORT%
echo   LAN     : http://%LAN_IP%:%PORT%
echo   Stop    : Ctrl+C
echo ============================================
"%CD%\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port %PORT%
pause