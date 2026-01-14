# PISAG Windows Installation Script
# Requires: Python 3.9+, Git, HackRF drivers
# Run as Administrator: powershell -ExecutionPolicy Bypass -File install.ps1

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\pisag",
    [string]$RepoUrl = "https://github.com/szeremeta1/pisag.git",
    [string]$Branch = "main",
    [decimal]$Frequency = 439.9875,
    [decimal]$TransmitPower = 10
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PISAG Windows Installation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script should be run as Administrator for full functionality."
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Check Python installation
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
    
    # Extract version number and check if >= 3.9
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
            Write-Error "Python 3.9 or higher is required. Found: $pythonVersion"
            exit 1
        }
    }
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.9+ from https://www.python.org/"
    exit 1
}

# Check Git installation
Write-Host "`nChecking Git installation..." -ForegroundColor Yellow
try {
    $gitVersion = & git --version 2>&1
    Write-Host "Found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Error "Git is not installed or not in PATH. Please install Git from https://git-scm.com/"
    exit 1
}

# Check if HackRF drivers are available
Write-Host "`nChecking HackRF installation..." -ForegroundColor Yellow
$hackrfInfo = & hackrf_info 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "HackRF detected successfully" -ForegroundColor Green
} else {
    Write-Warning "HackRF not detected. Please ensure:"
    Write-Warning "1. HackRF One is connected via USB"
    Write-Warning "2. Zadig drivers are installed (visit https://github.com/pbatard/libwdi/releases)"
    Write-Warning "3. HackRF tools are installed"
    $continue = Read-Host "Continue installation? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Create installation directory
Write-Host "`nCreating installation directory: $InstallDir" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# Clone or update repository
if (Test-Path "$InstallDir\.git") {
    Write-Host "Updating existing repository..." -ForegroundColor Yellow
    Push-Location $InstallDir
    & git fetch --all --prune
    & git checkout $Branch
    & git reset --hard "origin/$Branch"
    Pop-Location
} else {
    Write-Host "Cloning repository..." -ForegroundColor Yellow
    & git clone --branch $Branch $RepoUrl $InstallDir
}

Push-Location $InstallDir

# Create Python virtual environment
Write-Host "`nCreating Python virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $InstallDir "venv"
if (-not (Test-Path $venvPath)) {
    & python -m venv $venvPath
}

# Activate virtual environment
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $activateScript

# Upgrade pip
Write-Host "`nUpgrading pip..." -ForegroundColor Yellow
& python -m pip install --upgrade pip

# Install Python dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    & pip install -r requirements.txt
} else {
    Write-Error "requirements.txt not found in $InstallDir"
    Pop-Location
    exit 1
}

# Install SoapySDR (if not already installed)
Write-Host "`nChecking SoapySDR installation..." -ForegroundColor Yellow
$soapyInstalled = $false
try {
    $testResult = & python -c "import SoapySDR; print('installed')" 2>&1
    if ($testResult -match "installed") {
        $soapyInstalled = $true
        Write-Host "SoapySDR Python module already installed" -ForegroundColor Green
    }
} catch {
    # Module not installed
}

if (-not $soapyInstalled) {
    Write-Warning "SoapySDR Python module not found."
    Write-Host "Please install SoapySDR manually:" -ForegroundColor Yellow
    Write-Host "1. Download PothosSDR (includes SoapySDR) from:" -ForegroundColor Yellow
    Write-Host "   https://downloads.myriadrf.org/builds/PothosSDR/" -ForegroundColor Yellow
    Write-Host "2. Install and add to PATH" -ForegroundColor Yellow
    Write-Host "3. Install SoapySDR Python module:" -ForegroundColor Yellow
    Write-Host "   pip install SoapySDR" -ForegroundColor Yellow
}

# Apply database migrations
Write-Host "`nApplying database migrations..." -ForegroundColor Yellow
if (Test-Path "alembic") {
    & alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Database migration failed"
        Pop-Location
        exit 1
    }
} else {
    Write-Warning "Alembic directory not found, skipping migrations"
}

# Configure config.json
Write-Host "`nConfiguring application..." -ForegroundColor Yellow
$configPath = Join-Path $InstallDir "config.json"

if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
} else {
    $config = @{
        system = @{}
        pocsag = @{}
        gr_pocsag = @{}
        hackrf = @{}
        plugins = @{}
        web = @{}
    }
}

# Prompt for configuration if not provided
if (-not $Frequency) {
    $freqInput = Read-Host "Enter default frequency in MHz [439.9875]"
    if ($freqInput) {
        $Frequency = [decimal]$freqInput
    } else {
        $Frequency = 439.9875
    }
}

if (-not $TransmitPower) {
    $powerInput = Read-Host "Enter default transmit power in dB [10]"
    if ($powerInput) {
        $TransmitPower = [decimal]$powerInput
    } else {
        $TransmitPower = 10
    }
}

$config.system.frequency = $Frequency
$config.system.transmit_power = $TransmitPower

# Save config
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath
Write-Host "Configuration saved to $configPath" -ForegroundColor Green

# Create logs directory
$logsDir = Join-Path $InstallDir "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

# Create startup script
$startScript = Join-Path $InstallDir "start.ps1"
@"
# Start PISAG
`$ErrorActionPreference = "Stop"
`$ScriptDir = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$venvActivate = Join-Path `$ScriptDir "venv\Scripts\Activate.ps1"

Write-Host "Starting PISAG POCSAG Pager Server..." -ForegroundColor Cyan

if (-not (Test-Path `$venvActivate)) {
    Write-Error "Virtual environment not found. Please run install.ps1 first."
    pause
    exit 1
}

& `$venvActivate
Push-Location `$ScriptDir

`$pythonExe = Join-Path `$ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path `$pythonExe)) {
    Write-Error "Python executable not found. Virtual environment may be corrupted."
    Pop-Location
    pause
    exit 1
}

Write-Host "Web UI: http://localhost:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

try {
    & python -m pisag.app
} catch {
    Write-Error "Failed to start: `$_"
} finally {
    Pop-Location
}
"@ | Set-Content $startScript

# Create startup batch file for convenience
$startBatch = Join-Path $InstallDir "start.bat"
@"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
"@ | Set-Content $startBatch

Pop-Location

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nLEGAL WARNING:" -ForegroundColor Red
Write-Host "Radio transmission requires proper licensing and adherence to local regulations." -ForegroundColor Red
Write-Host "Operate only on authorized frequencies with appropriate power limits." -ForegroundColor Red
Write-Host "`n" -ForegroundColor Yellow
Write-Host "Installation directory: $InstallDir" -ForegroundColor Cyan
Write-Host "`nTo start PISAG:" -ForegroundColor Yellow
Write-Host "  Method 1: Double-click $InstallDir\start.bat" -ForegroundColor White
Write-Host "  Method 2: Run $InstallDir\start.ps1" -ForegroundColor White
Write-Host "  Method 3: Run manually:" -ForegroundColor White
Write-Host "    cd $InstallDir" -ForegroundColor Gray
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "    python -m pisag.app" -ForegroundColor Gray
Write-Host "`nWeb UI will be available at: http://localhost:5000" -ForegroundColor Cyan
Write-Host "API health check: http://localhost:5000/health" -ForegroundColor Cyan
Write-Host "`nFor Windows Service setup, see docs/SETUP_WINDOWS.md" -ForegroundColor Yellow
