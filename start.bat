@echo off
title Sweedle - 3D Asset Generator
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║   ███████╗██╗    ██╗███████╗███████╗██████╗ ██╗     ███████╗   ║
echo  ║   ██╔════╝██║    ██║██╔════╝██╔════╝██╔══██╗██║     ██╔════╝   ║
echo  ║   ███████╗██║ █╗ ██║█████╗  █████╗  ██║  ██║██║     █████╗     ║
echo  ║   ╚════██║██║███╗██║██╔══╝  ██╔══╝  ██║  ██║██║     ██╔══╝     ║
echo  ║   ███████║╚███╔███╔╝███████╗███████╗██████╔╝███████╗███████╗   ║
echo  ║   ╚══════╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═════╝ ╚══════╝╚══════╝   ║
echo  ║                                                           ║
echo  ║            Local 3D Asset Generator for Games             ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Check for Python
echo [1/5] Checking Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python not found!
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

:: Check for Node.js
echo [2/5] Checking Node.js installation...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Node.js not found!
    echo.
    echo  Please install Node.js from:
    echo  https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
echo        Found Node.js %NODE_VERSION%

:: Setup Python virtual environment
echo [3/5] Setting up Python environment...
if not exist "backend\venv" (
    echo        Creating virtual environment...
    python -m venv backend\venv
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate venv and install dependencies
call backend\venv\Scripts\activate.bat
echo        Installing Python dependencies (this may take a while first time)...
pip install -q -r backend\requirements.txt 2>nul
if %errorlevel% neq 0 (
    echo        Installing dependencies...
    pip install -r backend\requirements.txt
)

:: Setup frontend
echo [4/5] Setting up frontend...
cd frontend
if not exist "node_modules" (
    echo        Installing npm dependencies...
    call npm install --silent 2>nul
    if %errorlevel% neq 0 (
        call npm install
    )
)
cd ..

:: Start services
echo [5/5] Starting Sweedle...
echo.

:: Start backend in background
echo        Starting backend server...
start "Sweedle Backend" /min cmd /c "cd backend && ..\backend\venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000"

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in background
echo        Starting frontend server...
start "Sweedle Frontend" /min cmd /c "cd frontend && npm run dev"

:: Wait for frontend to start
timeout /t 3 /nobreak >nul

:: Open browser
echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║   Sweedle is starting up!                                 ║
echo  ║                                                           ║
echo  ║   Frontend: http://localhost:5173                         ║
echo  ║   Backend:  http://localhost:8000                         ║
echo  ║   API Docs: http://localhost:8000/docs                    ║
echo  ║                                                           ║
echo  ║   Opening browser...                                      ║
echo  ║                                                           ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

timeout /t 2 /nobreak >nul
start http://localhost:5173

echo  Press any key to stop Sweedle...
pause >nul

:: Cleanup - kill the servers
echo.
echo  Shutting down...
taskkill /fi "WINDOWTITLE eq Sweedle Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Sweedle Frontend*" /f >nul 2>&1

echo  Goodbye!
timeout /t 2 /nobreak >nul
