# PISAG Startup Script for Windows
# Activates virtual environment and starts the application

$ErrorActionPreference = "Stop"

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvActivate = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Starting PISAG POCSAG Pager Server" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path $VenvActivate)) {
    Write-Error "Virtual environment not found at: $VenvActivate"
    Write-Host "Please run install.ps1 first to set up PISAG" -ForegroundColor Yellow
    pause
    exit 1
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& $VenvActivate

# Change to application directory
Push-Location $ScriptDir

Write-Host "`nStarting application..." -ForegroundColor Yellow

# Verify Python is available
$pythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at: $pythonExe"
    Write-Host "Virtual environment may be corrupted. Try running install.ps1 again." -ForegroundColor Yellow
    Pop-Location
    pause
    exit 1
}

Write-Host "Web UI will be available at: http://localhost:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the application
try {
    & python -m pisag.app
} catch {
    Write-Error "Failed to start PISAG: $_"
} finally {
    Pop-Location
}
