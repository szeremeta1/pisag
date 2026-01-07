# PISAG - POCSAG Pager Server

Educational, hobby-friendly POCSAG pager transmission system for Raspberry Pi + HackRF One. PISAG provides a lightweight, extensible foundation for encoding and transmitting pager messages with a plugin-driven architecture, real-time web UI, and REST/SocketIO APIs. Built for learning and experimentation—use responsibly and legally.

## Key Features
- Web SPA with live status, send, history, settings tabs (Socket.IO real-time updates)
- REST API for send/history/pagers/config/analytics/status + health/readiness endpoints
- Plugin architecture for POCSAG encoder and SDR backends (SoapySDR HackRF by default)
- Transmission queue + worker thread with device monitor, pause/resume, and rich logging
- Hybrid configuration (JSON defaults + DB overrides) with runtime updates
- SQLite + Alembic migrations; transmission logs and analytics
- Rotating file logging with optional console output
- Designed for Raspberry Pi 3/4 in constrained environments

## Hardware Requirements
- Raspberry Pi 3 or newer
- HackRF One with appropriate antenna and USB cable
- Optional powered USB hub for stable power

## Software Requirements
- Python 3.9+
- SoapySDR with HackRF module (`soapysdr-module-hackrf`)
- SQLite (bundled on Raspberry Pi OS)
- System build deps for NumPy/SoapySDR

## Quick Start (summary)
1) Install deps (Pi): `sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip sqlite3 hackrf libhackrf-dev soapysdr-tools libsoapysdr-dev soapysdr-module-hackrf`
2) Clone and install:
```bash
git clone https://github.com/szeremeta1/pisag /opt/pisag
cd /opt/pisag
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m pisag.app
```
3) Browse to `http://<raspberry-pi-ip>:5000`

For full setup, see [docs/SETUP.md](docs/SETUP.md).

## Project Structure
```
pisag/
  app.py              # Flask app factory, SocketIO, error handlers, shutdown
  api/                # REST routes, SocketIO emitters
  services/           # Business logic, worker, queue, monitor, status manager
  plugins/            # Encoder/SDR plugin interfaces and implementations
  models/             # SQLAlchemy ORM models + Alembic migrations
  utils/              # Logging, database helpers
  config.py           # JSON+DB configuration loader
static/               # Vanilla JS SPA frontend
scripts/              # Seed/test helpers
logs/                 # Rotating application logs
config.json           # Default configuration
docs/                 # Documentation suite
pisag.service         # systemd unit (for Pi deployment)
install.sh            # Automated install script
```

## Documentation
- [Architecture](docs/ARCHITECTURE.md)
- [Setup (Raspberry Pi)](docs/SETUP.md)
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
