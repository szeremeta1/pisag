"""Background monitor for HackRF device connectivity."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from pisag.api.socketio import emit_status_update
from pisag.services.system_status import SystemStatus
from pisag.utils.logging import get_logger


class DeviceMonitor:
    def __init__(self, sdr, transmission_queue=None, config_provider: Optional[Callable[[], dict]] = None, check_interval: float = 5.0) -> None:
        self.sdr = sdr
        self.queue = transmission_queue
        self.config_provider = config_provider or (lambda: {})
        self.check_interval = check_interval
        self.logger = get_logger(__name__)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_connected = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("Device monitor started")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.logger.info("Device monitor stopped")

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                connected = False
                try:
                    connected = bool(self.sdr.is_connected())
                except Exception:
                    connected = False

                if not connected:
                    if self._last_connected:
                        self.logger.warning("HackRF disconnected; pausing queue")
                        SystemStatus.set_hackrf_status(False)
                        self._pause_queue()
                        emit_status_update({"hackrf_connected": False})
                    self._attempt_reconnect()
                else:
                    if not self._last_connected:
                        self.logger.info("HackRF connection restored")
                        SystemStatus.set_hackrf_status(True)
                        self._resume_queue()
                        emit_status_update({"hackrf_connected": True})
                self._last_connected = connected or SystemStatus.get_hackrf_status()
                time.sleep(self.check_interval)
            except Exception:
                self.logger.error("Device monitor loop error", exc_info=True)
                time.sleep(self.check_interval)

    def _attempt_reconnect(self) -> None:
        try:
            if self.sdr.connect():
                cfg = self.config_provider() or {}
                sys_cfg = cfg.get("system", {})
                pocsag_cfg = cfg.get("pocsag", {})
                frequency = float(sys_cfg.get("frequency", 439.9875))
                sample_rate = float(sys_cfg.get("sample_rate", 2.0))
                gain = float(sys_cfg.get("if_gain", 40))
                power = float(sys_cfg.get("transmit_power", 10))
                try:
                    self.sdr.configure(frequency, sample_rate, gain, power)
                except Exception:
                    self.logger.warning("Reconnected but failed to configure SDR", exc_info=True)
                SystemStatus.set_hackrf_status(True)
                emit_status_update({"hackrf_connected": True, "frequency": frequency, "baud_rate": pocsag_cfg.get("baud_rate")})
                self._resume_queue()
        except Exception:
            self.logger.debug("Reconnect attempt failed", exc_info=True)

    def _pause_queue(self) -> None:
        if hasattr(self.queue, "pause"):
            try:
                self.queue.pause()
            except Exception:
                self.logger.error("Failed to pause queue", exc_info=True)

    def _resume_queue(self) -> None:
        if hasattr(self.queue, "resume"):
            try:
                self.queue.resume()
            except Exception:
                self.logger.error("Failed to resume queue", exc_info=True)
