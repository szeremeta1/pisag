# Setup (Windows)

Step-by-step installation for Windows 10/11 with HackRF One.

## Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.9 or higher
- Git for Windows
- HackRF One with USB cable
- Administrator access for driver installation

## System Preparation

### 1. Install Python
Download and install Python 3.9+ from [python.org](https://www.python.org/downloads/)
- ✅ Check "Add Python to PATH" during installation
- Verify installation:
```powershell
python --version
```

### 2. Install Git
Download and install Git from [git-scm.com](https://git-scm.com/download/win)
- Use default installation options
- Verify installation:
```powershell
git --version
```

### 3. Install HackRF Drivers and Tools

#### Install Zadig (USB Driver)
1. Download Zadig from [zadig.akeo.ie](https://zadig.akeo.ie/)
2. Connect HackRF One via USB
3. Run Zadig as Administrator
4. Select `Options` → `List All Devices`
5. Select "HackRF One" from the dropdown
6. Choose "WinUSB" driver
7. Click "Install Driver" or "Replace Driver"

#### Install HackRF Tools
1. Download pre-built HackRF tools from [GitHub Releases](https://github.com/greatscottgadgets/hackrf/releases)
2. Extract to `C:\Program Files\HackRF`
3. Add `C:\Program Files\HackRF\bin` to System PATH
4. Verify installation:
```powershell
hackrf_info
```

### 4. Install SoapySDR (SDR Interface Library)

#### Option A: PothosSDR Suite (Recommended)
1. Download PothosSDR installer from [myriadrf.org](https://downloads.myriadrf.org/builds/PothosSDR/)
2. Run the installer (includes SoapySDR, drivers, and tools)
3. Add Pothos installation directory to PATH (e.g., `C:\Program Files\PothosSDR\bin`)
4. Verify installation:
```powershell
SoapySDRUtil --info
```

#### Option B: Build from Source
Follow [SoapySDR build instructions](https://github.com/pothosware/SoapySDR/wiki/BuildGuide)

### 5. Install SoapySDR Python Module
```powershell
pip install SoapySDR
```

## Automated Installation

Run the installation script as Administrator:

```powershell
# Open PowerShell as Administrator
cd C:\
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/szeremeta1/pisag/main/install.ps1 | iex"
```

Or download and run locally:
```powershell
git clone https://github.com/szeremeta1/pisag C:\pisag
cd C:\pisag
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer will:
- Check Python, Git, and HackRF installation
- Create virtual environment
- Install Python dependencies
- Apply database migrations
- Configure default settings (frequency, power)
- Create startup scripts

## Manual Installation

```powershell
# Clone repository
git clone https://github.com/szeremeta1/pisag C:\pisag
cd C:\pisag

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Optional: Seed test data
python scripts/seed_data.py

# Configure settings
notepad config.json

# Run the application
python -m pisag.app
```

Open your browser to `http://localhost:5000`

## Running PISAG on Windows

### Method 1: Startup Batch File (Easiest)
Double-click `start.bat` in the installation directory

### Method 2: PowerShell Script
```powershell
cd C:\pisag
.\start.ps1
```

### Method 3: Manual Start
```powershell
cd C:\pisag
.\venv\Scripts\Activate.ps1
python -m pisag.app
```

## Running as a Windows Service

For production use, run PISAG as a Windows Service using NSSM (Non-Sucking Service Manager).

### Install NSSM
1. Download NSSM from [nssm.cc](https://nssm.cc/download)
2. Extract `nssm.exe` to `C:\Program Files\NSSM`
3. Add to System PATH

### Create Service
```powershell
# Run as Administrator
cd C:\pisag

# Install service
nssm install PISAG "C:\pisag\venv\Scripts\python.exe" "-m pisag.app"
nssm set PISAG AppDirectory "C:\pisag"
nssm set PISAG DisplayName "PISAG POCSAG Pager Server"
nssm set PISAG Description "Educational POCSAG pager transmission system for HackRF One"
nssm set PISAG Start SERVICE_AUTO_START

# Start service
nssm start PISAG

# Check status
nssm status PISAG

# View logs
nssm set PISAG AppStdout "C:\pisag\logs\stdout.log"
nssm set PISAG AppStderr "C:\pisag\logs\stderr.log"
```

### Service Management
```powershell
# Start service
nssm start PISAG

# Stop service
nssm stop PISAG

# Restart service
nssm restart PISAG

# Remove service
nssm remove PISAG confirm
```

## Configuration

Edit `config.json` in the installation directory:
```json
{
  "system": {
    "frequency": 929.6125,
    "transmit_power": 10,
    "if_gain": 40,
    "sample_rate": 12.0
  },
  "web": {
    "host": "0.0.0.0",
    "port": 5000
  }
}
```

Settings can also be updated via the Web UI Settings tab.

## Firewall Configuration

Allow incoming connections to port 5000:
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "PISAG" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

## Verification

```powershell
# Check health endpoint
curl http://localhost:5000/health

# Check readiness
curl http://localhost:5000/health/ready

# Check system status
curl http://localhost:5000/api/status
```

Open Web UI at `http://localhost:5000` and verify:
- HackRF is detected in Dashboard
- Can send a test message

## Building Windows Executable

To create a standalone executable that doesn't require Python installation:

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --name="PISAG" `
            --onefile `
            --add-data "static;static" `
            --add-data "config.json;." `
            --hidden-import=eventlet `
            --hidden-import=dns `
            --hidden-import=SoapySDR `
            --icon=static/favicon.ico `
            pisag/app.py

# Executable will be in dist/PISAG.exe
```

See `build_windows.ps1` for the complete build script.

## Troubleshooting

### HackRF Not Detected
- Verify USB connection and LED indicators
- Check Device Manager for HackRF under "Universal Serial Bus devices"
- Reinstall WinUSB driver using Zadig
- Try a different USB port (USB 2.0 preferred)
- Use a powered USB hub if necessary

### SoapySDR Import Error
- Ensure PothosSDR is installed and in PATH
- Install SoapySDR Python module: `pip install SoapySDR`
- Restart PowerShell after PATH changes

### Permission Errors
- Run PowerShell as Administrator
- Check folder permissions in installation directory
- Disable antivirus temporarily during installation

### Port Already in Use
- Change port in `config.json`: `"port": 5001`
- Kill processes using port 5000: `netstat -ano | findstr :5000`

### Virtual Environment Issues
- Delete `venv` folder and recreate: `python -m venv venv`
- Ensure Python is in PATH
- Use PowerShell (not Command Prompt) for activation

## Performance Notes

Windows machines typically have:
- Faster processors than Raspberry Pi
- More RAM
- Better USB performance (3.0/3.1 support)
- Higher sample rates supported
- Lower latency RF transmission

This results in improved HackRF performance and transmission quality.

## Security Considerations

- Run PISAG with minimal required privileges
- Use firewall rules to restrict network access
- Keep Windows and drivers up to date
- Regular backups of configuration and database

## See Also
- [Troubleshooting](TROUBLESHOOTING.md)
- [Usage Guide](USAGE.md)
- [API Reference](API.md)
- [Legal / Regulatory](LEGAL.md)
