@echo off
title DarkWatch Full-Spectrum Endpoint Agent
color 0B
cd /d "%~dp0"

echo ========================================================
echo        DARKWATCH FULL-SPECTRUM ENDPOINT AGENT
echo ========================================================
echo [*] Working Directory: %CD%
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python was not found on PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo [*] Checking dependencies...
python -c "import requests, psutil, pynput, PIL, cv2" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required libraries...
    pip install requests psutil pynput Pillow opencv-python pywin32
)

echo [*] Launching Agent...
python -u telemetry_agent.py
pause
