@echo off
title Sweedle Tauri Debug Launcher
echo ========================================
echo   Sweedle - Tauri Debug Mode
echo ========================================
echo.
echo All services will run in separate terminals
echo with full debug output visible.
echo.

:: Check if Rust is installed
where rustc >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Rust is not installed!
    echo.
    echo Please install Rust first:
    echo   winget install Rustlang.Rustup
    echo.
    echo Then install Tauri CLI:
    echo   cargo install tauri-cli
    echo.
    pause
    exit /b 1
)

:: Check if Tauri CLI is installed
where cargo-tauri >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Tauri CLI not found. Installing...
    cargo install tauri-cli
)

echo [1/3] Starting Python backend (DEBUG MODE)...
start "Sweedle Backend - DEBUG" cmd /k "cd /d %~dp0backend && echo ======================================== && echo   SWEEDLE BACKEND - DEBUG MODE && echo ======================================== && echo. && venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug"

echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo [2/3] Starting Vite frontend (DEBUG MODE)...
cd /d %~dp0frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
start "Sweedle Frontend - DEBUG" cmd /k "cd /d %~dp0frontend && echo ======================================== && echo   SWEEDLE FRONTEND - DEBUG MODE && echo ======================================== && echo. && npm run dev"

echo Waiting for frontend to start...
timeout /t 5 /nobreak >nul

echo [3/3] Starting Tauri dev mode...
echo.
echo ========================================
echo   TAURI DEV MODE
echo ========================================
echo.
echo Backend:  http://localhost:8000 (see Backend terminal)
echo Frontend: http://localhost:5173 (see Frontend terminal)
echo API Docs: http://localhost:8000/docs
echo.
echo Close this window to stop Tauri.
echo Close the other terminals to stop backend/frontend.
echo ========================================
echo.

cd /d %~dp0src-tauri
cargo tauri dev

echo.
echo Tauri closed. Backend and Frontend terminals are still running.
echo Close them manually or press any key to kill all Sweedle processes.
pause

:: Cleanup - kill the servers
echo.
echo Shutting down all Sweedle processes...
taskkill /fi "WINDOWTITLE eq Sweedle Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Sweedle Frontend*" /f >nul 2>&1
echo Done.
