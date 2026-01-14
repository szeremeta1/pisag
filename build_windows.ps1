# PISAG Windows Executable Build Script
# Creates a standalone Windows executable using PyInstaller
# Run in virtual environment: .\venv\Scripts\Activate.ps1

param(
    [switch]$Clean = $false,
    [switch]$OneFile = $true,
    [string]$OutputDir = "dist",
    [string]$BuildDir = "build"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PISAG Windows Executable Builder" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check if in virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Warning "Not in virtual environment. Activating..."
    $venvPath = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        & $venvPath
    } else {
        Write-Error "Virtual environment not found. Run install.ps1 first."
        exit 1
    }
}

# Clean previous builds
if ($Clean) {
    Write-Host "`nCleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path $OutputDir) {
        Remove-Item -Recurse -Force $OutputDir
    }
    if (Test-Path $BuildDir) {
        Remove-Item -Recurse -Force $BuildDir
    }
    if (Test-Path "*.spec") {
        Remove-Item -Force *.spec
    }
}

# Install PyInstaller if not present
Write-Host "`nChecking PyInstaller..." -ForegroundColor Yellow
try {
    & python -c "import PyInstaller" 2>&1 | Out-Null
    Write-Host "PyInstaller already installed" -ForegroundColor Green
} catch {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & pip install pyinstaller
}

# Prepare build arguments
$pyinstallerArgs = @(
    "--name=PISAG",
    "--clean",
    "--noconfirm"
)

if ($OneFile) {
    $pyinstallerArgs += "--onefile"
} else {
    $pyinstallerArgs += "--onedir"
}

# Add data files
$pyinstallerArgs += @(
    "--add-data=static;static",
    "--add-data=config.json;.",
    "--add-data=alembic;alembic",
    "--add-data=alembic.ini;."
)

# Add hidden imports for dynamic imports and dependencies
$hiddenImports = @(
    "eventlet",
    "eventlet.hubs",
    "dns",
    "dns.rdtypes",
    "dns.rdtypes.ANY",
    "dns.rdtypes.IN",
    "engineio.async_drivers.eventlet",
    "socketio",
    "flask_socketio",
    "SoapySDR",
    "numpy",
    "sqlalchemy",
    "alembic",
    "bitstring"
)

foreach ($import in $hiddenImports) {
    $pyinstallerArgs += "--hidden-import=$import"
}

# Exclude unnecessary modules to reduce size
$excludeModules = @(
    "matplotlib",
    "PyQt5",
    "tkinter",
    "test",
    "unittest"
)

foreach ($exclude in $excludeModules) {
    $pyinstallerArgs += "--exclude-module=$exclude"
}

# Add icon if available
$iconPath = "static\favicon.ico"
if (Test-Path $iconPath) {
    $pyinstallerArgs += "--icon=$iconPath"
}

# Windows-specific options
$pyinstallerArgs += @(
    "--console",  # Show console for logging
    "--noupx"     # Disable UPX compression (compatibility)
)

# Entry point
$pyinstallerArgs += "pisag\app.py"

# Run PyInstaller
Write-Host "`nBuilding Windows executable..." -ForegroundColor Yellow
Write-Host "Arguments: $($pyinstallerArgs -join ' ')" -ForegroundColor Gray

& pyinstaller $pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Copy additional files to dist
Write-Host "`nCopying additional files..." -ForegroundColor Yellow
$distPath = if ($OneFile) { $OutputDir } else { Join-Path $OutputDir "PISAG" }

# Create necessary directories
$distDirs = @("logs", "EXTERNAL")
foreach ($dir in $distDirs) {
    $targetDir = Join-Path $distPath $dir
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    }
}

# Copy EXTERNAL directory if it exists
if (Test-Path "EXTERNAL") {
    Write-Host "Copying EXTERNAL directory..." -ForegroundColor Gray
    Copy-Item -Recurse -Force "EXTERNAL\*" (Join-Path $distPath "EXTERNAL")
}

# Copy documentation
$docs = @("README.md", "LICENSE")
foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Copy-Item $doc $distPath -Force
    }
}

if (Test-Path "docs") {
    $docsTarget = Join-Path $distPath "docs"
    if (-not (Test-Path $docsTarget)) {
        New-Item -ItemType Directory -Force -Path $docsTarget | Out-Null
    }
    Copy-Item -Recurse "docs\*" $docsTarget -Force
}

# Create default config if not exists
$configPath = Join-Path $distPath "config.json"
if (-not (Test-Path $configPath) -and (Test-Path "config.json")) {
    Copy-Item "config.json" $configPath -Force
}

# Create startup batch file
$batchPath = Join-Path $distPath "start.bat"
$batchContent = @"
@echo off
echo Starting PISAG POCSAG Pager Server...
echo.
echo Web UI will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
PISAG.exe
pause
"@
$batchContent | Set-Content $batchPath

# Create README for the distribution
$distReadme = Join-Path $distPath "README_DIST.txt"
$distReadmeContent = @"
PISAG - POCSAG Pager Server for Windows
========================================

Prerequisites:
1. HackRF One with Zadig WinUSB drivers installed
2. SoapySDR/PothosSDR installed (download from myriadrf.org)
3. Appropriate radio license and legal authorization

Quick Start:
1. Connect HackRF One via USB
2. Run start.bat or PISAG.exe
3. Open http://localhost:5000 in your browser
4. Configure settings and send test messages

Configuration:
- Edit config.json to change frequency, power, and other settings
- Settings can also be changed via the Web UI

Documentation:
- See docs/ folder for detailed documentation
- README.md for overview
- docs/SETUP_WINDOWS.md for Windows-specific setup
- docs/USAGE.md for usage instructions

Legal Warning:
Radio transmission requires proper licensing and adherence to local regulations.
Operate only on authorized frequencies with appropriate power limits.

For support and updates:
https://github.com/szeremeta1/pisag
"@
$distReadmeContent | Set-Content $distReadme

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nOutput location: $distPath" -ForegroundColor Cyan

if ($OneFile) {
    Write-Host "Executable: $(Join-Path $distPath 'PISAG.exe')" -ForegroundColor Cyan
} else {
    Write-Host "Run: $(Join-Path $distPath 'PISAG.exe')" -ForegroundColor Cyan
}

Write-Host "`nTo distribute:" -ForegroundColor Yellow
Write-Host "  1. Create a ZIP of the $distPath folder" -ForegroundColor White
Write-Host "  2. Ensure users have HackRF drivers and SoapySDR installed" -ForegroundColor White
Write-Host "  3. Include setup instructions (README_DIST.txt)" -ForegroundColor White

# Calculate size
$exePath = Join-Path $distPath "PISAG.exe"
if (Test-Path $exePath) {
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Host "`nExecutable size: $([math]::Round($exeSize, 2)) MB" -ForegroundColor Cyan
}
