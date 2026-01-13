# Usage Guide

The web UI is a four-tab SPA at `http://<ip>:5000` with real-time Socket.IO updates.

## Supported Devices

PISAG is designed to work with POCSAG alphanumeric pagers, including:
- **Motorola ADVISOR II™** (model A05DTS5962AA) operating at 929-932 MHz
- Other POCSAG-compatible pagers at frequencies from 1 MHz to 6 GHz (HackRF range)

The default frequency is set to 929.6125 MHz for Motorola ADVISOR II compatibility.

## Dashboard
- Status panel: HackRF connection, frequency, baud rate.
- Stats cards: Total messages, success rate, today's count, active pagers.
- Recent messages: Last 10 with timestamp, recipient, preview, status.
- System information: POCSAG deviation, FSK polarity, encoder type, SDR interface.
- Real-time: Updates via `status_update`, `history_update`, `analytics_update` events.

## Send
- Individual message: Select pager or enter 7-digit RIC, choose type (alphanumeric/numeric), enter message (80 chars max for alphanumeric), click Send. Progress shows queued -> encoding -> transmitting -> complete.
- Broadcast: Select multiple pagers via checkboxes or comma-separated RICs, choose type, enter message, click Send Broadcast. Same progress feedback.
- Message types: Alphanumeric (printable ASCII 0x20-0x7E), Numeric (digits 0-9, space, U, -, [, ]).

## History
- Paginated table (timestamp, recipients, message, type, frequency, duration, status, resend).
- Pagination controls (offset/limit 50 default); Refresh button; Resend action retransmits a prior message.

## Settings
- System config: Frequency (MHz), baud rate (512/1200/2400 bps), transmit power (0-15 dBm), IF gain (0-47 dB), sample rate (Hz).
- **POCSAG Encoder**: Choose between:
  - **GNU Radio (gr-pocsag)**: Uses GNU Radio flowgraph with HackRF. Recommended for production use.
  - **Pure Python**: Generates IQ samples directly in Python. Useful for testing or when GNU Radio is not available.
- Invert FSK: Enable for PDW compatibility when testing with RTL-SDR.
- Address book: Table of pagers (name, RIC, notes) with edit/delete. Add form to create new pagers.

## REST API Examples
```bash
# Send
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{"recipients": ["1234567"], "message": "Hello", "type": "alphanumeric"}'

# List messages
curl "http://localhost:5000/api/messages?limit=10"

# Resend
curl -X POST http://localhost:5000/api/messages/1/resend

# Pagers
curl http://localhost:5000/api/pagers
curl -X POST http://localhost:5000/api/pagers -H "Content-Type: application/json" -d '{"name": "Test", "ric_address": "1234567"}'

# Config
curl -X PUT http://localhost:5000/api/config -H "Content-Type: application/json" -d '{"system": {"frequency": 929.6125}}'

# Change encoder
curl -X PUT http://localhost:5000/api/config -H "Content-Type: application/json" -d '{"plugins": {"pocsag_encoder": "pure_python"}}'

# Get available encoders
curl http://localhost:5000/api/config/encoders

# Analytics
curl http://localhost:5000/api/analytics

# Status / Health
curl http://localhost:5000/api/status
curl http://localhost:5000/health
```

## Best Practices
- Start with low power; ensure licensed frequencies.
- Keep messages concise (<=80 chars).
- Use address book for frequent RICs.
- Check HackRF status before sending; monitor transmission logs for errors.
- Monitor health endpoints for readiness/liveness.
- For Motorola ADVISOR II pagers, use the default 929.6125 MHz frequency and 1200 baud rate.
