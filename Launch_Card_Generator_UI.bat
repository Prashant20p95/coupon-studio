@echo off
title Umang Utsav Coupons Soft Copy - Launcher
cd /d "%~dp0"
echo =========================================================
echo   Starting Umang Utsav Coupons Soft Copy Studio...
echo =========================================================
echo.
echo Freeing port 5000 if occupied by stale instances...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :5000') do (
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo Launching Server and Opening Dashboard...
start "" "http://localhost:5000"
python app.py
pause
