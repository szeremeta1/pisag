#!/usr/bin/env bash
set -euo pipefail

systemctl status "$SERVICE_NAME" --no-pager
echo "Install complete. Logs: journalctl -u $SERVICE_NAME -f"
APP_DIR="/opt/pisag"
VENV_DIR="$APP_DIR/venv"
REPO_URL="${REPO_URL:-"https://github.com/<repo>/pisag.git"}"
BRANCH="${BRANCH:-"main"}"
SERVICE_NAME="pisag.service"
PYTHON_BIN="python3"
APT_PACKAGES=(
  python3 python3-pip python3-venv git sqlite3 build-essential
  hackrf libhackrf-dev
  soapysdr-tools libsoapysdr-dev soapysdr-module-hackrf
)

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)."
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get is required to install system dependencies (HackRF/SoapySDR). Aborting."
  exit 1
fi

echo "Updating apt package index and upgrading base system..."
apt-get update -y
apt-get upgrade -y

echo "Installing required packages: ${APT_PACKAGES[*]}"
apt-get install -y "${APT_PACKAGES[@]}"

command -v git >/dev/null 2>&1 || { echo "git is required after package install"; exit 1; }
command -v $PYTHON_BIN >/dev/null 2>&1 || { echo "$PYTHON_BIN is required after package install"; exit 1; }

if [[ "$REPO_URL" == *"<repo>"* ]]; then
  read -r -p "Enter REPO_URL for git clone (e.g., https://github.com/owner/pisag.git): " input_url
  if [[ -n "$input_url" ]]; then
    REPO_URL="$input_url"
  fi
fi

if [[ -z "$REPO_URL" || "$REPO_URL" == *"<repo>"* ]]; then
  echo "REPO_URL is not set to a valid git URL. Export REPO_URL=https://github.com/<owner>/pisag.git and rerun."
  exit 1
fi

mkdir -p "$APP_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
  echo "Updating existing repo in $APP_DIR"
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  echo "Cloning $REPO_URL into $APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  $PYTHON_BIN -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt
fi

# Apply Alembic migrations if present
if [[ -d "alembic" ]]; then
  alembic upgrade head || {
    echo "Alembic migration failed"; exit 1;
  }
fi

CONFIG_FILE="$APP_DIR/config.json"
if [[ -f "$CONFIG_FILE" ]]; then
  current_freq=$(CONFIG_FILE="$CONFIG_FILE" python - <<'PY'
import json, os, pathlib
cfg = json.load(pathlib.Path(os.environ["CONFIG_FILE"]).open())
print(cfg.get("system", {}).get("frequency", ""))
PY
  )
  current_power=$(CONFIG_FILE="$CONFIG_FILE" python - <<'PY'
import json, os, pathlib
cfg = json.load(pathlib.Path(os.environ["CONFIG_FILE"]).open())
print(cfg.get("system", {}).get("transmit_power", ""))
PY
  )
else
  current_freq="439.9875"
  current_power="10"
  cat > "$CONFIG_FILE" <<'EOF'
{
  "system": {
    "frequency": 439.9875,
    "transmit_power": 10
  }
}
EOF
fi

if [[ -z "$current_freq" ]]; then
  current_freq="439.9875"
fi

if [[ -z "$current_power" ]]; then
  current_power="10"
fi

read -r -p "Default frequency in MHz [$current_freq]: " freq_input
read -r -p "Default transmit power (dB) [$current_power]: " power_input

freq_value=${freq_input:-$current_freq}
power_value=${power_input:-$current_power}

data["system"]["frequency"] = to_float("frequency", "$freq_value")
CONFIG_FILE="$CONFIG_FILE" FREQ_VALUE="$freq_value" POWER_VALUE="$power_value" python - <<'PY'
import json, os, pathlib, sys
cfg_path = pathlib.Path(os.environ["CONFIG_FILE"])
data = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
data.setdefault("system", {})

def to_float(name, value):
  try:
    return float(value)
  except Exception:
    print(f"Invalid {name}: {value}")
    sys.exit(1)

data["system"]["frequency"] = to_float("frequency", os.environ["FREQ_VALUE"])
data["system"]["transmit_power"] = to_float("transmit_power", os.environ["POWER_VALUE"])
cfg_path.write_text(json.dumps(data, indent=2))
print("Updated config.json with frequency and transmit_power")
PY

echo "Checking HackRF connectivity..."
if command -v hackrf_info >/dev/null 2>&1; then
  if hackrf_info; then
    echo "hackrf_info succeeded"
  else
    echo "hackrf_info failed; verify HackRF is connected" >&2
  fi
else
  echo "hackrf_info not found; ensure hackrf package installed" >&2
fi

echo "Checking SoapySDR HackRF binding..."
if command -v SoapySDRUtil >/dev/null 2>&1; then
  if SoapySDRUtil --find="driver=hackrf"; then
    echo "SoapySDRUtil detected HackRF"
  else
    echo "SoapySDRUtil did not detect HackRF; driver may be missing" >&2
  fi
else
  echo "SoapySDRUtil not found; ensure soapysdr-tools installed" >&2
fi

# Create logs dir and adjust permissions
mkdir -p "$APP_DIR/logs"
chown -R pi:pi "$APP_DIR"

# Install systemd service
cp "$APP_DIR/pisag.service" "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

systemctl status "$SERVICE_NAME" --no-pager || true

echo "------------------------------------------------------------"
echo "LEGAL / REGULATORY: Transmitting on radio frequencies may require licensing and must comply with local regulations. You are responsible for lawful operation."
echo "------------------------------------------------------------"
echo "Service is managed via systemd:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo systemctl restart $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "Web UI: http://<raspberry-pi-ip>:5000"
echo "API health: curl http://localhost:5000/health"
echo "Install complete. Logs: journalctl -u $SERVICE_NAME -f"
