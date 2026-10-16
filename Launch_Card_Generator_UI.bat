@echo off
title Umang Utsav Coupons Soft Copy - Launcher

:: Automatically locate the Card_Generator directory wherever this launcher is placed
if exist "%~dp0app.py" (
    cd /d "%~dp0"
) else if exist "%~dp0Card_Generator\app.py" (
    cd /d "%~dp0Card_Generator"
) else if exist "C:\Users\PrashantYadav\Desktop\Card_Generator\app.py" (
    cd /d "C:\Users\PrashantYadav\Desktop\Card_Generator"
)

echo =========================================================
echo   Starting Umang Utsav Coupons Soft Copy Studio...
echo =========================================================
echo Working Directory: %CD%
echo.
echo Freeing port 5000 if occupied by stale instances...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :5000') do (
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Launching Server and Opening Dashboard in your browser...
start "" "http://localhost:5000"
python app.py
pause
