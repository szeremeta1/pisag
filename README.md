# PISAG - POCSAG Pager Server

Educational, hobby-friendly POCSAG pager transmission system for **Windows, Linux, and Raspberry Pi** with HackRF One. PISAG provides a lightweight, extensible foundation for encoding and transmitting pager messages with a plugin-driven architecture, real-time web UI, and REST/SocketIO APIs. Built for learning and experimentation—use responsibly and legally.

## Platform Support
- ✅ **Windows 10/11** - Full support with superior performance
- ✅ **Linux** - Full support (Ubuntu, Debian, etc.)
- ✅ **Raspberry Pi** - Optimized for Pi 3/4 with Raspberry Pi OS

## Supported Devices
- **Motorola ADVISOR II™** (model A05DTS5962AA) at 929-932 MHz
- Other POCSAG-compatible pagers at VHF/UHF frequencies

## Key Features
- Web SPA with live status, send, history, settings tabs (Socket.IO real-time updates)
- REST API for send/history/pagers/config/analytics/status + health/readiness endpoints
- Plugin architecture for POCSAG encoder and SDR backends
- **Two encoder options**: GNU Radio (gr-pocsag) or Pure Python encoder
- Switchable encoders via web UI and config API
- Transmission queue + worker thread with device monitor, pause/resume, and rich logging
- Hybrid configuration (JSON defaults + DB overrides) with runtime updates
- SQLite + Alembic migrations; transmission logs and analytics
- Rotating file logging with optional console output
- Designed for Raspberry Pi 3/4 in constrained environments
- **GNU Radio + gr-pocsag pipeline** - Proven HackRF/POCSAG flowgraph decodable on PDW and real pagers

## Hardware Requirements
- **For Windows/Linux PC**: Modern x86_64 computer with USB 2.0/3.0 port
- **For Raspberry Pi**: Raspberry Pi 3 or newer (Pi 4 recommended)
- HackRF One with appropriate antenna and USB cable
- Optional powered USB hub for stable power delivery

## Software Requirements

### All Platforms
- Python 3.9+
- HackRF drivers and tools
- SoapySDR (SDR interface library)
- SQLite (usually pre-installed)

### Platform-Specific
- **Windows**: PothosSDR suite, Zadig WinUSB drivers
- **Linux/Raspberry Pi**: GNU Radio + gr-osmosdr packages

## Quick Start

Choose your platform:

### 🪟 Windows (PowerShell as Administrator)
```powershell
# Prerequisites: Python 3.9+, Git, HackRF drivers, PothosSDR
# Download installer and run
irm https://raw.githubusercontent.com/szeremeta1/pisag/main/install.ps1 | iex
```
Or download and run locally:
```powershell
git clone https://github.com/szeremeta1/pisag C:\pisag
cd C:\pisag
powershell -ExecutionPolicy Bypass -File install.ps1
# Follow prompts, then run start.bat
```
See **[docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md)** for detailed Windows setup.

### 🐧 Linux / Raspberry Pi
```bash
# Install system dependencies
sudo apt-get update && sudo apt-get install -y \
  python3 python3-venv python3-pip sqlite3 \
  hackrf libhackrf-dev gnuradio gr-osmosdr python3-gnuradio

# Clone and install
git clone https://github.com/szeremeta1/pisag /opt/pisag
cd /opt/pisag
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m pisag.app
```
Browse to `http://<device-ip>:5000`

See **[docs/SETUP.md](docs/SETUP.md)** for detailed Linux/Raspberry Pi setup.

## Project Structure
```
pisag/
  app.py              # Flask app factory, SocketIO, error handlers, shutdown
  api/                # REST routes, SocketIO emitters
  services/           # Business logic, worker, queue, monitor, status manager
  plugins/            # Encoder/SDR plugin interfaces and implementations
  models/             # SQLAlchemy ORM models + Alembic migrations
  utils/              # Logging, database helpers, platform detection
  config.py           # JSON+DB configuration loader
static/               # Vanilla JS SPA frontend
scripts/              # Seed/test helpers
logs/                 # Rotating application logs
config.json           # Default configuration
docs/                 # Documentation suite
install.sh            # Linux/Pi automated install script
install.ps1           # Windows automated install script
build_windows.ps1     # Windows executable builder (PyInstaller)
pisag.service         # systemd unit (for Linux/Pi deployment)
```

## Windows Executable Package

Build a standalone Windows executable that doesn't require Python installation:

```powershell
cd C:\pisag
.\venv\Scripts\Activate.ps1
.\build_windows.ps1
# Output: dist/PISAG.exe
```

The executable includes:
- All Python dependencies bundled
- Web UI static files
- Database migrations
- Configuration files
- Documentation

Distribute the `dist/` folder as a portable application. Users only need HackRF drivers and SoapySDR installed.

## Performance: Windows vs. Raspberry Pi

**Windows machines offer significant advantages:**
- ⚡ **Faster processors** (multi-core, higher clock speeds)
- 💾 **More RAM** (8-32GB typical vs. 1-8GB on Pi)
- 🔌 **Better USB** (USB 3.0/3.1 support, higher bandwidth)
- 📡 **Higher sample rates** (better RF quality)
- ⏱️ **Lower latency** (faster processing and transmission)

This results in improved HackRF performance, transmission quality, and system responsiveness.

## Documentation
- [Architecture](docs/ARCHITECTURE.md)
- **[Setup - Windows](docs/SETUP_WINDOWS.md)** ⭐
- **[Setup - Linux/Raspberry Pi](docs/SETUP.md)** ⭐
- [Usage Guide](docs/USAGE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [POCSAG Protocol](docs/POCSAG.md)
- [Legal / Regulatory](docs/LEGAL.md)
- [API Reference](docs/API.md)
- [Database](docs/DATABASE.md)

## Legal Warning
Radio transmission requires proper licensing and adherence to local regulations. Operate only on authorized frequencies with appropriate power limits. Use in controlled, legal environments. The authors and contributors assume no liability for misuse.

## Contributing
Contributions are welcome for educational improvements, docs, and robustness fixes. Please keep the project’s educational focus and safety in mind.

## License
MIT License. See LICENSE if provided in this repository.
