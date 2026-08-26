@echo off
cd /d "%~dp0"
rem LOCAL mode: Cookie Secure OFF so LAN devices over http://IP:8000 keep sessions.
rem For public/frp tunnel use, run start-prod.bat instead.
setlocal enabledelayedexpansion
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set "LANIP=%%a"
set "LANIP=%LANIP: =%"
echo ============================================
echo   ZUA-2026 BlackBox Server [LOCAL MODE]
echo   Cookie Secure : OFF (local / LAN testing)
echo   Local         : http://127.0.0.1:8000
echo   LAN           : http://%LANIP%:8000
echo   Public        : use start-prod.bat instead
echo   Stop          : Ctrl+C
echo ============================================
"%CD%\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --no-server-header
pause
