# Troubleshooting

## Platform-Specific Issues

### Windows

#### HackRF Not Detected on Windows
- **Symptoms**: Dashboard shows Disconnected; `/health` reports `hackrf: false`; `hackrf_info` fails.
- **Checks**: 
  - Device Manager shows HackRF under "Universal Serial Bus devices" or "libusb devices"
  - WinUSB driver installed via Zadig
  - USB cable and port working
  - Try different USB port (USB 2.0 ports often more reliable)
- **Fix**: 
  - Reinstall WinUSB driver using Zadig (as Administrator)
  - Use a powered USB hub
  - Restart Windows after driver installation
  - Try different USB cable

#### SoapySDR Import Error on Windows
- **Symptoms**: `ImportError: No module named 'SoapySDR'` or `DLL load failed`
- **Checks**: PothosSDR installed; PATH includes PothosSDR bin directory
- **Fix**: 
  - Install PothosSDR from [myriadrf.org](https://downloads.myriadrf.org/builds/PothosSDR/)
  - Add `C:\Program Files\PothosSDR\bin` to System PATH
  - Install Python module: `pip install SoapySDR`
  - Restart PowerShell/terminal after PATH changes

#### PowerShell Execution Policy Error
- **Symptoms**: `start.ps1` fails with "cannot be loaded because running scripts is disabled"
- **Fix**: Run PowerShell as Administrator and execute:
  ```powershell
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
  Or run scripts with bypass:
  ```powershell
  powershell -ExecutionPolicy Bypass -File start.ps1
  ```

#### Port Already in Use (Windows)
- **Symptoms**: "Address already in use" error on startup
- **Checks**: 
  ```powershell
  netstat -ano | findstr :5000
  ```
- **Fix**: 
  - Kill process using the port (use PID from netstat)
  - Change port in `config.json`: `"port": 5001`

#### Windows Service Won't Start
- **Symptoms**: NSSM service fails to start or crashes immediately
- **Checks**: Event Viewer → Windows Logs → Application
- **Fix**: 
  - Verify paths in NSSM configuration
  - Check Python virtual environment is accessible
  - Ensure working directory is correct
  - Review `logs/stdout.log` and `logs/stderr.log`

#### Antivirus/Windows Defender Blocking
- **Symptoms**: Installation fails; executable won't run; network connections blocked
- **Fix**: 
  - Add installation directory to Windows Defender exclusions
  - Add `PISAG.exe` to exclusions
  - Allow through Windows Firewall for port 5000

### Linux / Raspberry Pi

#### HackRF Not Detected
- Symptoms: Dashboard shows Disconnected; `/health` reports `hackrf: false`.
- Checks: USB connection; powered hub; `hackrf_info`; `gnuradio-config-info --version`; `dmesg` for USB errors.
- Fix: Reseat USB, different port, ensure `gnuradio`, `gr-osmosdr`, and HackRF drivers are installed; provide adequate power.

## Common Issues (All Platforms)

### Transmission Failures
- Symptoms: Messages stuck queued/encoding; errors in logs or transmission_logs table.
- Checks: HackRF connected; frequency valid; power 0-15 dBm; sample rate/gain reasonable; CPU load.
- Fix: Reconnect HackRF; restart service; lower power/gain; verify config via Settings/API; inspect logs.

### PDW Paging Decoder Not Receiving
- Symptoms: RTL-SDR + PDW shows no decodes; frequency is correct.
- Checks: FSK polarity setting; frequency accuracy; RTL-SDR tuning; PDW configuration; software version.
- Fix: Enable "Invert FSK" in Settings tab (should be on by default); verify frequency matches exactly; check RTL-SDR gain settings; ensure PDW is set to the baud rate you are transmitting (default 1200 baud with gr-pocsag).
- Note: Versions prior to the gr-pocsag integration may have produced undecodable messages. Ensure you're running the latest version.

### Web Interface Not Loading
- Symptoms: Cannot reach `http://<ip>:5000`.
- Checks: `systemctl status pisag`; `ps aux | grep pisag`; firewall/port conflicts.
- Fix: Restart service; free port 5000; review `journalctl -u pisag -f`.

### Database Errors
- Symptoms: 503 errors, "Database unavailable".
- Checks: File permissions; disk space; `alembic upgrade head`; `sqlite3 pisag.db ".schema"`.
- Fix: Run migrations; adjust permissions; ensure SQLite present.

### Configuration Issues
- Symptoms: Invalid frequency/power; config not persisting.
- Checks: `config.json` syntax; value ranges (frequency 1-6000 MHz, power 0-15 dBm, sample rate 2-30 MHz); DB overrides in `system_config` table.
- Fix: Correct values; update via API/Settings; restart service.

## Performance Considerations

### Performance on Raspberry Pi
- Symptoms: Slow encoding/transmission; high CPU.
- Fix: Use Pi 3/4; close other processes; reduce sample rate; monitor temperature; ensure good cooling.

### SocketIO Issues
- Symptoms: Real-time updates missing.
- Checks: Browser console; Socket.IO client/server versions; CORS; network stability.
- Fix: Refresh page; clear cache; try another browser; ensure service running.

### Performance on Windows PC
- **Advantages**: Windows PCs typically have faster CPUs, more RAM, and better USB bandwidth than Raspberry Pi
- **Higher Sample Rates**: Windows can handle higher sample rates (up to 20 MHz) for better RF quality
- **Lower Latency**: Faster transmission processing and encoding
- **Recommendation**: Use USB 3.0 ports for best performance; ensure adequate cooling

## Diagnostics

### Log Locations

#### Windows
- Application: `C:\pisag\logs\pisag.log` (or install directory)
- Service logs: `C:\pisag\logs\stdout.log` and `C:\pisag\logs\stderr.log` (if using NSSM)
- Event Viewer: Windows Logs → Application (filter by PISAG)

#### Linux / Raspberry Pi
- Application: `logs/pisag.log`
- Systemd: `journalctl -u pisag -f`
- Database: `transmission_logs` table

## Debug Mode
- Increase verbosity: set `log_level: "DEBUG"` in `config.json`.
- Flask debug: set `web.debug` true (not for production).
