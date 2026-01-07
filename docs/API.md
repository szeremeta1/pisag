# API Reference

Base URL: `http://<host>:5000/api`
Content-Type: `application/json`
Authentication: none (single-user system)
Error format: `{ "error": "message", "timestamp": "ISO8601", "details": {...} }`

## REST Endpoints
- **POST /api/send** — Send message
  - Body: `{ "recipients": ["1234567"], "message": "Hello", "type": "alphanumeric" }`
  - Responses: 201 success; 400 validation; 503 unavailable

- **GET /api/messages** — List messages
  - Query: `offset` (default 0), `limit` (default 50)
  - Responses: 200 success; 503 DB unavailable

- **POST /api/messages/:id/resend** — Resend message
  - Responses: 201 success; 404 not found; 503 DB unavailable

- **GET /api/pagers** — List pagers
  - Responses: 200 success; 503 DB unavailable

- **POST /api/pagers** — Create pager
  - Body: `{ "name": "Test", "ric_address": "1234567", "notes": "Optional" }`
  - Responses: 201 success; 400 validation/duplicate; 503 DB unavailable

- **PUT /api/pagers/:id** — Update pager
  - Body: `{ "name": "Updated", "ric_address": "7654321" }`
  - Responses: 200 success; 404 not found; 400 validation; 503 DB unavailable

- **DELETE /api/pagers/:id** — Delete pager
  - Responses: 200 success; 404 not found; 503 DB unavailable

- **GET /api/config** — Get configuration
  - Responses: 200 success; 503 DB unavailable

- **PUT /api/config** — Update configuration
  - Body: `{ "system": { "frequency": 440.0, "transmit_power": 12 } }`
  - Responses: 200 success; 400 validation; 503 DB unavailable

- **GET /api/analytics** — Get analytics
  - Responses: 200 success; 503 DB unavailable

- **GET /api/status** — System status
  - Response: `{ "hackrf_connected": true, "worker_running": true, "frequency": 439.9875, "baud_rate": 512, "queue_size": 0 }`
  - Responses: 200 success; 503 service unavailable

- **GET /health** — Health check
  - Response: `{ "status": "healthy|degraded|unhealthy", "checks": {"database": true, "hackrf": true, "config": true}, "uptime_seconds": 123, "queue_size": 0, "timestamp": "..." }`
  - Responses: 200 healthy/degraded; 503 unhealthy

- **GET /health/ready** — Readiness check
  - Responses: 200 ready; 503 not ready

## Socket.IO Events
- **Client → Server**: `connect`, `disconnect`, `subscribe_updates`, `unsubscribe_updates`
- **Server → Client** (broadcast to "updates" room):
  - `message_queued` — `{ "message_id": 1, "recipients": 1, "timestamp": "..." }`
  - `encoding_started` — `{ "message_id": 1, "stage": "encoding" }`
  - `transmitting` — `{ "message_id": 1, "stage": "transmitting", "ric": "1234567" }`
  - `transmission_complete` — `{ "message_id": 1, "status": "success", "duration": 1.23 }`
  - `transmission_failed` — `{ "message_id": 1, "status": "failed", "error": "..." }`
  - `status_update` — `{ "hackrf_connected": false, ... }`
  - `history_update` — `{ "message_id": 1 }`
  - `analytics_update` — `{}`

## Python Example
```python
import requests
BASE_URL = "http://localhost:5000/api"
resp = requests.post(f"{BASE_URL}/send", json={
    "recipients": ["1234567"],
    "message": "Hello from Python",
    "type": "alphanumeric",
})
print(resp.json())
```

## JavaScript Socket.IO Example
```javascript
const socket = io('http://localhost:5000');
socket.on('connect', () => {
  socket.emit('subscribe_updates');
});
socket.on('transmission_complete', (data) => {
  console.log(`Message ${data.message_id} sent in ${data.duration}s`);
});
```
