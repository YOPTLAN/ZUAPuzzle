@echo off
cd /d "%~dp0"
rem PROD mode: Cookie Secure ON (browser only sends it over HTTPS), no auto-reload.
rem NOTE: rate limiting is in-process memory based; keep single worker (no --workers).
set "ZUA_COOKIE_SECURE=1"
echo ============================================
echo   ZUA-2026 BlackBox Server [PROD MODE]
echo   Cookie Secure : ON  (HTTPS / frp tunnel)
echo   Local         : http://127.0.0.1:8000
echo   Stop          : Ctrl+C
echo ============================================
"%CD%\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --no-server-header
pause
