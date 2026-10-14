@echo off
chcp 65001 >nul
title ZzzFort-LocalChat — Launcher

set ZZZFORT=C:\ZzzFort

echo.
echo ============================================================
echo   ZzzFort-LocalChat — Starting
echo ============================================================
echo.

:: --- Check if manager already running ---
netstat -ano | findstr ":8090 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
  echo [!] Manager already running on 8090 — skipping
) else (
  echo [1/3] Starting model-manager.py...
  start "ZzzFort-Manager" /MIN cmd /c "cd /d %ZZZFORT% && venv\Scripts\python.exe model-manager.py"
)

:: --- Check if HTTP server already running ---
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
  echo [!] HTTP server already running on 8000 — skipping
) else (
  echo [2/3] Starting HTTP server for chat...
  start "ZzzFort-WebServer" /MIN cmd /c "cd /d %ZZZFORT% && venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1"
)

echo [3/3] Waiting for model to load (40 seconds)...
timeout /t 40 /nobreak >nul

echo Opening chat in browser...
start "" "http://127.0.0.1:8000/chat.html"

echo.
echo ============================================================
echo   Ready!
echo ============================================================
echo.
echo   Two minimized windows:
echo     - ZzzFort-Manager    (model control, port 8090)
echo     - ZzzFort-WebServer  (chat.html server, port 8000)
echo.
echo   To stop everything:
echo     1. Close those two windows
echo     2. Run: taskkill /F /IM llama-server.exe
echo     3. Run: taskkill /F /IM python.exe   (optional — kills all Python)
echo.
timeout /t 8 /nobreak >nul