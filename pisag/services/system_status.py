"""Thread-safe system status tracking for HackRF and worker state."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


class SystemStatus:
    _hackrf_connected: bool = False
    _last_transmission_time: Optional[datetime] = None
    _error_count: int = 0
    _uptime_start: datetime = datetime.now(timezone.utc)
    _lock = threading.Lock()

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._hackrf_connected = False
            cls._last_transmission_time = None
            cls._error_count = 0
            cls._uptime_start = datetime.now(timezone.utc)

    @classmethod
    def set_hackrf_status(cls, connected: bool) -> None:
        with cls._lock:
            cls._hackrf_connected = bool(connected)

    @classmethod
    def get_hackrf_status(cls) -> bool:
        with cls._lock:
            return cls._hackrf_connected

    @classmethod
    def record_transmission(cls) -> None:
        with cls._lock:
            cls._last_transmission_time = datetime.now(timezone.utc)

    @classmethod
    def increment_error_count(cls) -> None:
        with cls._lock:
            cls._error_count += 1

    @classmethod
    def get_uptime(cls) -> float:
        with cls._lock:
            return (datetime.now(timezone.utc) - cls._uptime_start).total_seconds()

    @classmethod
    def get_status_dict(cls, queue_size: int = 0) -> dict:
        with cls._lock:
            return {
                "hackrf_connected": cls._hackrf_connected,
                "last_transmission_time": cls._last_transmission_time.isoformat() if cls._last_transmission_time else None,
                "error_count": cls._error_count,
                "uptime_seconds": (datetime.now(timezone.utc) - cls._uptime_start).total_seconds(),
                "queue_size": queue_size,
            }
