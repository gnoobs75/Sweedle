# Sweedle Launcher - PowerShell Edition
# Double-click this file or run: powershell -ExecutionPolicy Bypass -File Start-Sweedle.ps1

$Host.UI.RawUI.WindowTitle = "Sweedle - 3D Asset Generator"

Write-Host @"

  ███████╗██╗    ██╗███████╗███████╗██████╗ ██╗     ███████╗
  ██╔════╝██║    ██║██╔════╝██╔════╝██╔══██╗██║     ██╔════╝
  ███████╗██║ █╗ ██║█████╗  █████╗  ██║  ██║██║     █████╗
  ╚════██║██║███╗██║██╔══╝  ██╔══╝  ██║  ██║██║     ██╔══╝
  ███████║╚███╔███╔╝███████╗███████╗██████╔╝███████╗███████╗
  ╚══════╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═════╝ ╚══════╝╚══════╝

  Local 3D Asset Generator for Game Development

"@ -ForegroundColor Cyan

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ERROR: Python not found!" -ForegroundColor Red
    Write-Host "  Install Python 3.10+ from: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "  Make sure to check 'Add Python to PATH'" -ForegroundColor White
    Read-Host "Press Enter to exit"
    exit 1
}
$pyVersion = python --version
Write-Host "  OK: $pyVersion" -ForegroundColor Green

# Check Node.js
Write-Host "[2/4] Checking Node.js..." -ForegroundColor Yellow
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "  ERROR: Node.js not found!" -ForegroundColor Red
    Write-Host "  Install from: https://nodejs.org/" -ForegroundColor White
    Read-Host "Press Enter to exit"
    exit 1
}
$nodeVersion = node --version
Write-Host "  OK: Node.js $nodeVersion" -ForegroundColor Green

# Setup Python venv
Write-Host "[3/4] Setting up Python environment..." -ForegroundColor Yellow
$venvPath = Join-Path $ScriptDir "backend\venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Gray
    python -m venv "$venvPath"
}

# Activate and install deps
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
. $activateScript

Write-Host "  Installing dependencies..." -ForegroundColor Gray
pip install -q -r backend\requirements.txt 2>$null
if ($LASTEXITCODE -ne 0) {
    pip install -r backend\requirements.txt
}
Write-Host "  OK: Backend ready" -ForegroundColor Green

# Setup frontend
Write-Host "[4/4] Setting up frontend..." -ForegroundColor Yellow
Set-Location frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "  Installing npm packages..." -ForegroundColor Gray
    npm install --silent 2>$null
}
if (-not (Test-Path "dist")) {
    Write-Host "  Building frontend..." -ForegroundColor Gray
    npm run build
}
Set-Location $ScriptDir
Write-Host "  OK: Frontend ready" -ForegroundColor Green

# Start server
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Sweedle on http://localhost:8000" -ForegroundColor White
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Open browser after delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:8000"
} | Out-Null

# Run server
Set-Location backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
