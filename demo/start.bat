@echo off
cd /d "%~dp0"
echo ============================================
echo   ZUA-2026 BlackBox Server (auto-reload ON)
echo   Local   : http://127.0.0.1:8000
echo   LAN     : http://192.168.31.123:8000
echo   Stop    : Ctrl+C
echo ============================================
"%CD%\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --no-server-header
pause
