# Setup (Raspberry Pi)

Step-by-step installation for Raspberry Pi 3/4 with Raspberry Pi OS.

## Prerequisites
- Raspberry Pi 3 or newer running Raspberry Pi OS (Bullseye or newer)
- HackRF One connected via USB (powered hub recommended)
- Internet access and basic Linux command-line familiarity

## System Preparation
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y \
  python3 python3-pip python3-venv git sqlite3 \
  hackrf libhackrf-dev gnuradio gr-osmosdr python3-gnuradio
```
Verify hardware:
```bash
hackrf_info
gnuradio-config-info --version
```

## Manual Installation
```bash
# Clone repository
sudo git clone <repo-url> /opt/pisag
cd /opt/pisag

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Python deps
pip install --upgrade pip
pip install -r requirements.txt

# Database
alembic upgrade head
# Optional seed
python scripts/seed_data.py
# Optional DB smoke test
python scripts/test_database.py

# Configure defaults (frequency, power, baud, gr-pocsag path)
nano config.json

# Run
python -m pisag.app
```
Open `http://<raspberry-pi-ip>:5000`.

## Automated Installation
Use the provided installer:
```bash
curl -sSL <script-url> | sudo bash
```
Follow prompts for frequency/power. The script installs deps, clones the repo, sets up venv, initializes the DB, and configures systemd.

## Systemd Service
```bash
sudo cp pisag.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pisag
sudo systemctl start pisag
sudo systemctl status pisag
sudo journalctl -u pisag -f
```

## Configuration
- Edit `config.json` for defaults (frequency, transmit_power, if_gain, sample_rate, log_level).
- Use the Settings tab in the web UI for runtime updates; DB overrides persist across restarts.

## Verification
```bash
curl http://localhost:5000/health          # health
curl http://localhost:5000/health/ready    # readiness
curl http://localhost:5000/api/status      # status
```
Confirm HackRF connected in Dashboard; send a test message.

## Troubleshooting
See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md).
