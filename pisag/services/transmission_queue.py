"""Thread-safe transmission queue."""

from __future__ import annotations

import queue
import threading
from typing import Any, Dict, List, Optional

from pisag.utils.logging import get_logger


class TransmissionQueue:
    """Simple FIFO queue for transmission requests."""

    def __init__(self) -> None:
        self._queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self._lock = threading.Lock()
        self._paused = False
        self.logger = get_logger(__name__)

    def enqueue(self, request: Dict[str, Any]) -> bool:
        required = {"message_id", "recipients", "message_text", "message_type", "frequency", "baud_rate"}
        if not required.issubset(request.keys()):
            raise ValueError("Request missing required keys")
        recipients = request.get("recipients")
        if not isinstance(recipients, list) or any(
            not isinstance(r, dict) or "ric" not in r or "pager_id" not in r for r in recipients
        ):
            raise ValueError("Recipients must be a list of dicts with ric and pager_id")
        with self._lock:
            self._queue.put(request)
        self.logger.info(
            "Enqueued transmission request",
            extra={"message_id": request.get("message_id"), "recipients": len(recipients)},
        )
        return True

    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if self._paused:
            self.logger.debug("Dequeue blocked: queue paused")
            return None
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def size(self) -> int:
        return self._queue.qsize()

    def is_empty(self) -> bool:
        return self._queue.empty()

    def pause(self) -> None:
        with self._lock:
            self._paused = True
        self.logger.warning("Transmission queue paused")

    def resume(self) -> None:
        with self._lock:
            self._paused = False
        self.logger.info("Transmission queue resumed")
