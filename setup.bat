@echo off
title Sweedle - Setup
color 0A

echo.
echo  ======================================
echo    Sweedle Setup
echo  ======================================
echo.

cd /d "%~dp0"

:: Check for Python
echo [1/4] Checking Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python not found in PATH!
    echo.
    echo  Please install Python 3.10+ from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo        Found Python %PYTHON_VERSION%

:: Create virtual environment
echo.
echo [2/4] Creating Python virtual environment...
if not exist "backend\venv" (
    python -m venv backend\venv
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo        Virtual environment created
) else (
    echo        Virtual environment already exists
)

:: Install Python dependencies
echo.
echo [3/4] Installing Python dependencies...
echo        This may take several minutes on first run...
backend\venv\Scripts\pip.exe install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  WARNING: Some dependencies may have failed to install.
    echo  The backend may still work with core functionality.
    echo.
)

:: Check for Node.js and setup frontend
echo.
echo [4/4] Setting up frontend...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  WARNING: Node.js not found. Frontend setup skipped.
    echo  Install Node.js from: https://nodejs.org/
    echo.
) else (
    for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo        Found Node.js !NODE_VERSION!

    cd frontend
    if not exist "node_modules" (
        echo        Installing npm dependencies...
        call npm install
    ) else (
        echo        npm dependencies already installed
    )
    cd ..
)

echo.
echo  ======================================
echo    Setup Complete!
echo  ======================================
echo.
echo  You can now run:
echo    - start.bat           : Start both frontend and backend
echo    - start-backend-debug.bat : Start backend with visible output
echo.
pause
