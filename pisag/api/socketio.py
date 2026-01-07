"""SocketIO event handlers and emitters."""

from __future__ import annotations

from datetime import datetime

from flask_socketio import join_room, leave_room

from pisag.utils.logging import get_logger

_socketio = None
_logger = get_logger(__name__)


def register_socketio(socketio) -> None:
    global _socketio
    _socketio = socketio

    @socketio.on("connect")
    def _connect():  # pragma: no cover - runtime
        _logger.info("SocketIO client connected")
        join_room("updates")

    @socketio.on("disconnect")
    def _disconnect():  # pragma: no cover - runtime
        _logger.info("SocketIO client disconnected")

    @socketio.on("subscribe_updates")
    def _subscribe_updates():  # pragma: no cover - runtime
        join_room("updates")
        socketio.emit("subscribed", {"status": "subscribed"})

    @socketio.on("unsubscribe_updates")
    def _unsubscribe_updates():  # pragma: no cover - runtime
        leave_room("updates")
        socketio.emit("unsubscribed", {"status": "unsubscribed"})


def _emit(event: str, payload: dict) -> None:
    if _socketio is None:
        return
    _socketio.emit(event, payload, room="updates")


def emit_message_queued(message_id: int, recipients_count: int) -> None:
    _emit(
        "message_queued",
        {"message_id": message_id, "recipients": recipients_count, "timestamp": datetime.utcnow().isoformat()},
    )


def emit_encoding_started(message_id: int) -> None:
    _emit("encoding_started", {"message_id": message_id, "stage": "encoding"})


def emit_transmitting(message_id: int, ric: str) -> None:
    _emit("transmitting", {"message_id": message_id, "stage": "transmitting", "ric": ric})


def emit_transmission_complete(message_id: int, duration: float) -> None:
    _emit(
        "transmission_complete",
        {"message_id": message_id, "status": "success", "duration": duration},
    )
    _emit("history_update", {"message_id": message_id})
    _emit("analytics_update", {})


def emit_transmission_failed(message_id: int, error: str) -> None:
    _emit("transmission_failed", {"message_id": message_id, "status": "failed", "error": error})
    _emit("history_update", {"message_id": message_id})


def emit_status_update(status_data: dict) -> None:
    _emit("status_update", status_data)
