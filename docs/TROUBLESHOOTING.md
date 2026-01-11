# Troubleshooting

## HackRF Not Detected
- Symptoms: Dashboard shows Disconnected; `/health` reports `hackrf: false`.
- Checks: USB connection; powered hub; `hackrf_info`; `gnuradio-config-info --version`; `dmesg` for USB errors.
- Fix: Reseat USB, different port, ensure `gnuradio`, `gr-osmosdr`, and HackRF drivers are installed; provide adequate power.

## Transmission Failures
- Symptoms: Messages stuck queued/encoding; errors in logs or transmission_logs table.
- Checks: HackRF connected; frequency valid; power 0-15 dBm; sample rate/gain reasonable; CPU load.
- Fix: Reconnect HackRF; restart service; lower power/gain; verify config via Settings/API; inspect logs.

## PDW Paging Decoder Not Receiving
- Symptoms: RTL-SDR + PDW shows no decodes; frequency is correct.
- Checks: FSK polarity setting; frequency accuracy; RTL-SDR tuning; PDW configuration; software version.
- Fix: Enable "Invert FSK" in Settings tab (should be on by default); verify frequency matches exactly; check RTL-SDR gain settings; ensure PDW is set to the baud rate you are transmitting (default 1200 baud with gr-pocsag).
- Note: Versions prior to the gr-pocsag integration may have produced undecodable messages. Ensure you're running the latest version.

## Web Interface Not Loading
- Symptoms: Cannot reach `http://<ip>:5000`.
- Checks: `systemctl status pisag`; `ps aux | grep pisag`; firewall/port conflicts.
- Fix: Restart service; free port 5000; review `journalctl -u pisag -f`.

## Database Errors
- Symptoms: 503 errors, "Database unavailable".
- Checks: File permissions; disk space; `alembic upgrade head`; `sqlite3 pisag.db ".schema"`.
- Fix: Run migrations; adjust permissions; ensure SQLite present.

## Configuration Issues
- Symptoms: Invalid frequency/power; config not persisting.
- Checks: `config.json` syntax; value ranges (frequency 1-6000 MHz, power 0-15 dBm, sample rate 2-30 MHz); DB overrides in `system_config` table.
- Fix: Correct values; update via API/Settings; restart service.

## Performance on Raspberry Pi
- Symptoms: Slow encoding/transmission; high CPU.
- Fix: Use Pi 3/4; close other processes; reduce sample rate; monitor temperature; ensure good cooling.

## SocketIO Issues
- Symptoms: Real-time updates missing.
- Checks: Browser console; Socket.IO client/server versions; CORS; network stability.
- Fix: Refresh page; clear cache; try another browser; ensure service running.

## Log Locations
- Application: `logs/pisag.log`
- Systemd: `journalctl -u pisag -f`
- Database: `transmission_logs` table

## Debug Mode
- Increase verbosity: set `log_level: "DEBUG"` in `config.json`.
- Flask debug: set `web.debug` true (not for production).
