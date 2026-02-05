@echo off
title ViralClipper AI Launcher
cd /d "%~dp0"

echo.
echo ========================================================
echo       ViralClipper AI - Dashboard Launcher
echo ========================================================
echo.

:: 1. Check if Python is installed globally
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10 and ensure "Add to PATH" is checked.
    pause
    exit /b
)

:: 2. Launch App
echo [System] Launching App UI...
python app_ui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ App crashed or closed with an error.
    pause
)
