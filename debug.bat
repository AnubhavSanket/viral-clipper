@echo off
:: FORCE PAUSE ON ERROR
if "%1"=="nested" goto :main
cmd /k "%~f0" nested
exit /b

:main
cls
title ViralClipper AI - DEBUG MODE
echo.
echo ========================================================
echo       ViralClipper AI - DEBUG LAUNCHER
echo ========================================================
echo.

:: 1. DEFINE PATHS (Edit these if your path is different)
set "PY_GLOBAL=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
set "PY_PORTABLE=python\python.exe"

:: 2. SEARCH FOR PYTHON
if exist "%PY_GLOBAL%" (
    set "TARGET_PY=%PY_GLOBAL%"
    echo [OK] Found Global Python 3.10
    goto :INSTALL_DEPS
)

if exist "%PY_PORTABLE%" (
    set "TARGET_PY=%PY_PORTABLE%"
    echo [OK] Found Portable Python
    goto :INSTALL_DEPS
)

:: IF NOT FOUND
echo [ERROR] Python 3.10 not found in standard locations.
echo Checked:
echo   1. %PY_GLOBAL%
echo   2. %PY_PORTABLE%
echo.
echo Please double-check your installation path.
goto :end

:INSTALL_DEPS
echo.
echo [System] Using: "%TARGET_PY%"
"%TARGET_PY%" --version

echo.
echo [System] Checking dependencies...
"%TARGET_PY%" -c "import PyQt6; import whisperx; print('Dependencies OK')" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Dependencies already installed.
    goto :RUN_APP
)

echo [INFO] Installing missing libraries...
"%TARGET_PY%" -m pip install PyQt6 requests pillow ollama matplotlib
"%TARGET_PY%" -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
"%TARGET_PY%" -m pip install git+https://github.com/m-bain/whisperx.git

:RUN_APP
echo.
echo [System] Launching app_ui.py...
"%TARGET_PY%" app_ui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRASH] Python exited with error code %ERRORLEVEL%
)

:end
echo.
echo ========================================================
echo                 SESSION ENDED
echo ========================================================
pause
