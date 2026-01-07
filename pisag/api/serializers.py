"""Serialization helpers for API responses."""

from __future__ import annotations

from typing import Any, Dict

from pisag.models import Message, MessageRecipient, Pager


def _iso(dt) -> str | None:  # type: ignore[override]
    return dt.isoformat() if dt else None


def serialize_pager(pager: Pager) -> Dict[str, Any]:
    return {
        "id": pager.id,
        "name": pager.name,
        "ric_address": pager.ric_address,
        "notes": pager.notes,
        "created_at": _iso(pager.created_at),
        "updated_at": _iso(pager.updated_at),
    }


def serialize_recipient(recipient: MessageRecipient) -> Dict[str, Any]:
    pager = recipient.pager
    return {
        "ric_address": recipient.ric_address,
        "pager_id": pager.id if pager else None,
        "pager_name": pager.name if pager else None,
    }


def serialize_message(message: Message) -> Dict[str, Any]:
    return {
        "id": message.id,
        "message_text": message.message_text,
        "message_type": message.message_type,
        "timestamp": _iso(message.timestamp),
        "status": message.status,
        "frequency": message.frequency,
        "baud_rate": message.baud_rate,
        "duration": message.duration,
        "error_message": message.error_message,
        "recipients": [serialize_recipient(r) for r in message.recipients],
    }


def serialize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config
