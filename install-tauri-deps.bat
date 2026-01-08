@echo off
title Sweedle - Install Tauri Dependencies
echo ========================================
echo   Sweedle - Installing Tauri Dependencies
echo ========================================
echo.

:: Check for Rust
echo Checking for Rust...
where rustc >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Rust not found. Installing via winget...
    winget install Rustlang.Rustup
    echo.
    echo Please restart your terminal after Rust installation completes,
    echo then run this script again.
    pause
    exit /b 1
) else (
    echo Rust found:
    rustc --version
)
echo.

:: Install Tauri CLI
echo Installing Tauri CLI...
cargo install tauri-cli
echo.

:: Install frontend Tauri dependency
echo Installing frontend Tauri packages...
cd /d %~dp0frontend
call npm install @tauri-apps/api @tauri-apps/cli
echo.

:: Verify installation
echo ========================================
echo   Verification
echo ========================================
echo.
echo Rust version:
rustc --version
echo.
echo Cargo version:
cargo --version
echo.
echo Tauri CLI version:
cargo tauri --version
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Run 'start-tauri-dev.bat' for development
echo   2. Run 'build-tauri.bat' for production build
echo.

pause
