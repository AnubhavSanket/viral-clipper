@echo off
title ViralClipper AI Launcher
echo.
echo ========================================================
echo        ViralClipper AI - Portable Launcher
echo ========================================================
echo.

set PY_PATH=python\python.exe

:: 1. Check if Python folder exists
if not exist "%PY_PATH%" (
    echo CRITICAL ERROR: 'python' folder not found.
    echo Please ensure the embedded python folder is extracted here.
    echo.
    pause
    exit
)

:: 2. Check/Install Pip (First run only)
if not exist "python\get-pip.py" (
    echo [System] First run detected. Configuring environment...
    curl -sS https://bootstrap.pypa.io/get-pip.py -o python\get-pip.py
    "%PY_PATH%" python\get-pip.py --no-warn-script-location >nul 2>&1
    del python\get-pip.py
)

:: 3. Run the App
echo [System] Launching Application...
"%PY_PATH%" app_ui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ App crashed or closed with an error.
    pause
)
