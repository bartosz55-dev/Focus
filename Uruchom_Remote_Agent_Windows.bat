@echo off
title Focus - Remote Desktop Testing Agent (Antigravity AI Bridge)
color 0B
cd /d "%~dp0"

echo =================================================================
echo       FOCUS REMOTE DESKTOP & TESTING AGENT (WINDOWS)
echo =================================================================
echo.

:: Detect Python
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
    echo Using Virtualenv: venv\Scripts\python.exe
) else (
    echo Using System Python: python
)

:: Ensure Pillow is installed for screenshots
echo Checking Pillow dependencies...
%PYTHON_CMD% -c "import PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing Pillow for high-res screen capture...
    %PYTHON_CMD% -m pip install pillow --quiet
)

echo.
echo Launching Focus Remote Testing Agent on port 8765...
echo =================================================================
%PYTHON_CMD% focus_remote_agent.py

echo.
echo =================================================================
echo Agent closed.
pause
