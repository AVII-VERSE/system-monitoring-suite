@echo off
title DarkWatch Suite Controller
color 0A
cd /d "%~dp0"

echo ========================================================
echo        DARKWATCH INTELLIGENCE & TELEMETRY SUITE
echo ========================================================
echo [*] Working Directory: %CD%

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python was not found on PATH. Please install Python 3.10+
    pause
    exit /b 1
)

:LOOP
echo.
echo [*] Launching DarkWatch Core Engine...
echo [*] Dashboard live at: http://127.0.0.1:5000
echo.

python -u main.py

echo.
echo [!] DarkWatch terminated. Restarting in 5 seconds...
echo [!] Press Ctrl+C to stop.
timeout /t 5 /nobreak >nul
goto LOOP
