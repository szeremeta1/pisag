"""Background transmission worker that dequeues, encodes, and transmits messages."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

import numpy as np

from pisag.config import get_config
from pisag.models import Message, TransmissionLog
from pisag.models.base import get_db_session
from pisag.plugins.base import ConfigurationError, EncodingError, TransmissionError, load_plugin
from pisag.services.system_status import SystemStatus
from pisag.utils.logging import get_logger
from pisag.api.socketio import (
    emit_encoding_started,
    emit_message_queued,
    emit_transmission_complete,
    emit_transmission_failed,
    emit_status_update,
    emit_transmitting,
)


class TransmissionWorker:
    """Dequeues transmission requests, encodes messages, and transmits via SDR."""

    def __init__(self, transmission_queue, config_path: str = "config.json") -> None:
        self.queue = transmission_queue
        self.config_path = config_path
        self.logger = get_logger(__name__)
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.config = get_config(config_path)
        encoder_class = self.config.get("plugins", {}).get("pocsag_encoder")
        sdr_class = self.config.get("plugins", {}).get("sdr_interface")
        self.encoder = load_plugin("encoder", encoder_class)
        self.sdr = load_plugin("sdr", sdr_class)
        self.encoder_handles_tx = hasattr(self.encoder, "encode_and_transmit")

    # Lifecycle -----------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        connected = False
        if not self.encoder_handles_tx:
            try:
                connected = self.sdr.connect()
            except Exception:
                connected = False
        else:
            connected = True

        if not connected:
            self.logger.warning("SDR not connected at startup; running in degraded mode")
            SystemStatus.set_hackrf_status(False)
            emit_status_update({"hackrf_connected": False})

        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        self.logger.info("Transmission worker started")
        if connected:
            SystemStatus.set_hackrf_status(True)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=10.0)
            if self._thread.is_alive():
                self.logger.warning("Transmission worker thread did not stop within timeout")
        try:
            self.sdr.disconnect()
        except Exception:
            self.logger.error("Failed to disconnect SDR during stop", exc_info=True)
        self.logger.info("Transmission worker stopped")

    # Processing ----------------------------------------------------------
    def _worker_loop(self) -> None:
        while self._running:
            request = self.queue.dequeue(block=True, timeout=1.0)
            if request is None:
                continue
            try:
                self._process_request(request)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.error("Unhandled error processing transmission request", exc_info=True)
                SystemStatus.increment_error_count()

    def _process_request(self, request: Dict[str, Any]) -> None:
        message_id = request["message_id"]
        recipients = request["recipients"]
        message_text = request["message_text"]
        message_type = request["message_type"]
        frequency = float(request["frequency"])
        baud_rate = int(request["baud_rate"])

        sys_cfg = self.config.get("system", {})
        sample_rate = float(sys_cfg.get("sample_rate", 12.0))
        gain = float(sys_cfg.get("if_gain", 40))
        power = float(sys_cfg.get("transmit_power", 10))

        self.logger.info("═" * 65)
        self.logger.info(
            "▶ STARTING TRANSMISSION REQUEST",
            extra={
                "message_id": message_id,
                "recipient_count": len(recipients),
                "message_length": len(message_text),
                "message_type": message_type,
                "frequency_mhz": frequency,
                "baud_rate": baud_rate,
                "sample_rate_mhz": sample_rate,
                "if_gain_db": gain,
                "tx_power_dbm": power,
            },
        )
        self.logger.info(f"Message: {repr(message_text)}")
        for idx, r in enumerate(recipients, 1):
            self.logger.info(f"  → Recipient {idx}: RIC {r.get('ric')}")

        start_time = time.time()
        details = f"Encoding started (baud={baud_rate}, type={message_type}, len={len(message_text)})"
        self._update_message_status(message_id, "encoding")
        self._create_log_entry(message_id, "encoding", details)
        emit_encoding_started(message_id)

        try:
            for idx, recipient in enumerate(recipients, 1):
                ric = recipient.get("ric")
                self.logger.info(
                    f"Processing recipient {idx}/{len(recipients)}: RIC {ric}",
                    extra={"message_id": message_id, "ric": ric, "recipient_index": idx},
                )
                if self.encoder_handles_tx:
                    self._update_message_status(message_id, "transmitting")
                    self._create_log_entry(
                        message_id,
                        "transmitting",
                        f"Transmitting via gr-pocsag to RIC {ric} at {frequency} MHz (baud={baud_rate})",
                    )
                    emit_transmitting(message_id, ric)
                    self.encoder.encode_and_transmit(
                        ric, message_text, message_type, baud_rate, frequency, gain, power
                    )
                    self.logger.info(f"Transmission completed for RIC {ric} using gr-pocsag")
                    SystemStatus.set_hackrf_status(True)
                else:
                    iq_samples = self.encoder.encode(ric, message_text, message_type, baud_rate)
                    self.logger.info(
                        "Encoded samples generated",
                        extra={
                            "message_id": message_id,
                            "ric": ric,
                            "sample_count": len(iq_samples),
                            "sample_dtype": str(iq_samples.dtype),
                            "is_complex": np.iscomplexobj(iq_samples),
                        },
                    )
                    self._update_message_status(message_id, "transmitting")
                    self._create_log_entry(
                        message_id,
                        "transmitting",
                        f"Transmitting to RIC {ric} at {frequency} MHz (sr={sample_rate} MHz, gain={gain} dB, power={power} dBm)",
                    )
                    emit_transmitting(message_id, ric)
                    self.logger.info("Configuring SDR for transmission")
                    self.sdr.configure(frequency, sample_rate, gain, power)
                    self.logger.info("Starting SDR transmission")
                    self.sdr.transmit(iq_samples)
                    self.logger.info(f"Transmission completed for RIC {ric}")

            duration = time.time() - start_time
            self._update_message_status(message_id, "success")
            self._create_log_entry(message_id, "complete", f"Transmission complete in {duration:.2f}s")
            emit_transmission_complete(message_id, duration)
            SystemStatus.record_transmission()
            self.logger.info(
                "✓ TRANSMISSION COMPLETE - Message sent successfully",
                extra={
                    "message_id": message_id,
                    "duration_s": round(duration, 2),
                    "recipients": len(recipients),
                    "frequency_mhz": frequency,
                },
            )
        except (EncodingError, ConfigurationError, TransmissionError) as exc:
            self._handle_error(message_id, recipients, exc)
        except Exception as exc:  # pragma: no cover - defensive catch
            self._handle_error(message_id, recipients, exc)

    def _handle_error(self, message_id: int, recipients: Any, exc: Exception) -> None:
        error_msg = str(exc)
        if isinstance(exc, TransmissionError):
            SystemStatus.set_hackrf_status(False)
            try:
                self.sdr.disconnect()
            except Exception:
                self.logger.error("Failed to disconnect SDR after transmission error", exc_info=True)
            if hasattr(self.queue, "pause"):
                try:
                    self.queue.pause()
                except Exception:
                    self.logger.error("Failed to pause queue after transmission error", exc_info=True)
            emit_status_update({"hackrf_connected": False})
        self.logger.error(
            "Transmission failed",
            extra={"message_id": message_id, "recipients": recipients, "error": error_msg},
            exc_info=True,
        )
        self._update_message_status(message_id, "failed", error_msg)
        self._create_log_entry(message_id, "error", f"{exc.__class__.__name__}: {error_msg}")
        emit_transmission_failed(message_id, error_msg)
        SystemStatus.increment_error_count()

    # DB helpers ----------------------------------------------------------
    def _update_message_status(self, message_id: int, status: str, error_message: Optional[str] = None) -> None:
        with get_db_session() as session:
            message = session.get(Message, message_id)
            if message is None:
                self.logger.error("Message not found for status update", extra={"message_id": message_id})
                return
            message.status = status
            if error_message:
                message.error_message = error_message

    def _create_log_entry(self, message_id: int, stage: str, details: Optional[str] = None) -> None:
        with get_db_session() as session:
            log_entry = TransmissionLog(message_id=message_id, stage=stage, details=details)
            session.add(log_entry)
