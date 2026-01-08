@echo off
title Sweedle Backend - Debug Mode
color 0E

echo.
echo  ======================================
echo    Sweedle Backend - DEBUG MODE
echo  ======================================
echo.

cd /d "%~dp0"

echo Current directory: %CD%
echo.

:: Check if backend folder exists
if not exist "backend" (
    echo  ERROR: backend folder not found!
    echo  Make sure you're running from the Sweedle root directory.
    pause
    exit /b 1
)

echo Checking for virtual environment...
echo Looking for: %CD%\backend\venv\Scripts\python.exe

:: Check if venv exists
if not exist "backend\venv\Scripts\python.exe" (
    echo.
    echo  Virtual environment not found. Creating it now...
    echo.

    :: Try py launcher with Python 3.11 or 3.12 (3.14 is too new for many packages)
    py -3.12 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python 3.12 via py launcher:
        py -3.12 --version
        echo.
        echo Creating venv with Python 3.12...
        py -3.12 -m venv backend\venv
        goto :check_venv
    )

    py -3.11 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python 3.11 via py launcher:
        py -3.11 --version
        echo.
        echo Creating venv with Python 3.11...
        py -3.11 -m venv backend\venv
        goto :check_venv
    )

    :: Try default py launcher (but warn about version)
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python via py launcher:
        py --version
        echo.
        echo WARNING: Python 3.14 is too new for some packages.
        echo          Install Python 3.11 or 3.12 for best compatibility.
        echo          https://www.python.org/downloads/release/python-3119/
        echo.
        echo Creating venv with py launcher...
        py -m venv backend\venv
        goto :check_venv
    )

    :: Try python command
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python:
        python --version
        echo.
        echo Creating venv...
        python -m venv backend\venv
        goto :check_venv
    )

    :: Neither worked
    echo.
    echo  ============================================
    echo   ERROR: Python not found!
    echo  ============================================
    echo.
    echo  Please install Python 3.10 or later from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, make sure to check:
    echo  [x] "Add Python to PATH"
    echo.
    echo  After installing, close this window and run again.
    echo.
    pause
    exit /b 1

:check_venv
    if not exist "backend\venv\Scripts\python.exe" (
        echo  ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )

    echo.
    echo Virtual environment created successfully!
    echo Installing dependencies... (this may take a few minutes)
    echo.

    :: Check Python version - use minimal requirements for 3.14+
    backend\venv\Scripts\python.exe -c "import sys; exit(0 if sys.version_info >= (3, 14) else 1)" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using minimal requirements for Python 3.14+ compatibility...
        backend\venv\Scripts\pip.exe install -r backend\requirements-minimal.txt
    ) else (
        backend\venv\Scripts\pip.exe install -r backend\requirements.txt
    )
)

echo.
echo Using Python from: backend\venv\Scripts\python.exe
echo.

:: Verify Python works
backend\venv\Scripts\python.exe --version
if %errorlevel% neq 0 (
    echo  ERROR: Python in venv is not working!
    pause
    exit /b 1
)

echo.
echo Starting backend with full output...
echo ----------------------------------------
echo.

cd backend
venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

echo.
echo ----------------------------------------
echo Backend exited with code %ERRORLEVEL%
echo Press any key to close...
pause
