@echo off
title Sweedle Tauri Build
echo ========================================
echo   Sweedle - Building Desktop App
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
    pause
    exit /b 1
)

:: Check if Tauri CLI is installed
where cargo-tauri >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Tauri CLI not found. Installing...
    cargo install tauri-cli
)

echo [1/3] Installing frontend dependencies...
cd /d %~dp0frontend
call npm install

echo [2/3] Building frontend...
call npm run build

echo [3/3] Building Tauri application...
cd /d %~dp0src-tauri
cargo tauri build

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Installer location:
echo   %~dp0src-tauri\target\release\bundle\
echo.
echo Executable location:
echo   %~dp0src-tauri\target\release\sweedle.exe
echo.

pause
