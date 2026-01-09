@echo off
title Sweedle Tauri Dev
echo ========================================
echo   Sweedle - Tauri Development Mode
echo ========================================
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

echo [1/4] Starting Python backend...
start "Sweedle Backend" cmd /c "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/4] Installing frontend dependencies if needed...
cd /d %~dp0frontend
if not exist node_modules (
    call npm install
)

echo [3/4] Starting Vite dev server...
start "Sweedle Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo Waiting for frontend to start...
timeout /t 5 /nobreak >nul

echo [4/4] Starting Tauri dev mode...
cd /d %~dp0src-tauri
cargo tauri dev

pause
