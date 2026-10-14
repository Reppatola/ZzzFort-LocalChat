@echo off
chcp 65001 >nul
title ZzzFort-LocalChat — Backup

set ZZZFORT=C:\ZzzFort
set PROJECT=%ZZZFORT%\_project
set BACKUP_DIR=%PROJECT%\backup

echo.
echo ============================================================
echo   ZzzFort-LocalChat — Backup
echo ============================================================
echo.

:: --- Create backup directory ---
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: --- Timestamp for this backup ---
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set LDT=%%a
set DATE=%LDT:~0,4%-%LDT:~4,2%-%LDT:~6,2%
set TIME=%LDT:~8,2%-%LDT:~10,2%-%LDT:~12,2%

set STAMP=%DATE%_%TIME%

echo [1/4] Copying working scripts...

if exist "%ZZZFORT%\chat.html" (
  copy /Y "%ZZZFORT%\chat.html" "%BACKUP_DIR%\chat.html" >nul
  echo    - chat.html
) else (
  echo    [!] chat.html not found in C:\ZzzFort\
)

if exist "%ZZZFORT%\model-manager.py" (
  copy /Y "%ZZZFORT%\model-manager.py" "%BACKUP_DIR%\model-manager.py" >nul
  echo    - model-manager.py
) else (
  echo    [!] model-manager.py not found in C:\ZzzFort\
)

if exist "%ZZZFORT%\start-chat.bat" (
  copy /Y "%ZZZFORT%\start-chat.bat" "%BACKUP_DIR%\start-chat.bat" >nul
  echo    - start-chat.bat
) else (
  echo    [!] start-chat.bat not found in C:\ZzzFort\
)

echo.
echo [2/4] Listing models...

if exist "%ZZZFORT%\diskllm\models" (
  for /d %%d in ("%ZZZFORT%\diskllm\models\*") do (
    echo    - %%~nxd
  )
) else (
  echo    [!] models directory not found
)

echo.
echo [3/4] Creating ZIP archive...

set ZIP_NAME=ZzzFort_backup_%STAMP%.zip
set ZIP_PATH=%BACKUP_DIR%\%ZIP_NAME%

where powershell >nul 2>&1
if %errorlevel%==0 (
  powershell -Command "Compress-Archive -Path '%PROJECT%\*' -DestinationPath '%ZIP_PATH%' -Force"
  if exist "%ZIP_PATH%" (
    echo    Created: %ZIP_NAME%
  ) else (
    echo    [!] Failed to create ZIP
  )
) else (
  echo    [!] PowerShell not found — skipping ZIP
)

echo.
echo [4/4] Rotating old backups (keeping last 5)...

pushd "%BACKUP_DIR%"
for /f "skip=5 delims=" %%f in ('dir /b /o-d ZzzFort_backup_*.zip 2^>nul') do (
  echo    Removing old: %%f
  del "%%f" >nul 2>&1
)
popd

echo.
echo ============================================================
echo   Backup complete!
echo   Location: %BACKUP_DIR%
echo ============================================================
echo.
echo   Files backed up:
echo     - chat.html
echo     - model-manager.py
echo     - start-chat.bat
echo     - ZIP archive of entire project
echo.
echo   Old backups (beyond 5 newest) were removed.
echo.
timeout /t 5 /nobreak >nul