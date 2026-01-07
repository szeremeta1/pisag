"""Message service handling validation, persistence, and queueing."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from pisag.models import Message, MessageRecipient, Pager
from pisag.utils.logging import get_logger
from pisag.utils.query_helpers import get_message_with_recipients
from pisag.utils.validation import (
    sanitize_message_text,
    validate_message_content,
    validate_message_length,
    validate_ric_format,
)


class MessageService:
    def __init__(self, transmission_queue) -> None:
        self.queue = transmission_queue
        self.logger = get_logger(__name__)

    def send_message(
        self,
        session: Session,
        recipients: List[str],
        message_text: str,
        message_type: str,
        frequency: float,
        baud_rate: int,
    ) -> Message:
        cleaned_recipients = self._normalize_recipients(recipients)
        self._validate_inputs(cleaned_recipients, message_text, message_type)

        sanitized_text = sanitize_message_text(message_text, message_type)
        message = Message(
            message_text=sanitized_text,
            message_type=message_type,
            status="queued",
            frequency=frequency,
            baud_rate=baud_rate,
            timestamp=datetime.utcnow(),
        )
        session.add(message)
        session.flush()

        recipient_records = []
        for ric in cleaned_recipients:
            pager = Pager.find_by_ric(session, ric)
            recipient = MessageRecipient(
                message_id=message.id,
                pager_id=pager.id if pager else None,
                ric_address=ric,
            )
            session.add(recipient)
            recipient_records.append({"ric": ric, "pager_id": pager.id if pager else None})

        session.commit()

        request = {
            "message_id": message.id,
            "recipients": recipient_records,
            "message_text": sanitized_text,
            "message_type": message_type,
            "frequency": frequency,
            "baud_rate": baud_rate,
        }
        self.queue.enqueue(request)
        self.logger.info("Message enqueued", extra={"message_id": message.id, "recipients": len(recipient_records)})
        return message

    def get_message_history(self, session: Session, offset: int = 0, limit: int = 50) -> List[Message]:
        return Message.get_history(session, offset=offset, limit=limit)

    def resend_message(self, session: Session, message_id: int) -> Message:
        original = get_message_with_recipients(session, message_id)
        if original is None:
            raise ValueError("Message not found")
        recipients = [r.ric_address for r in original.recipients]
        return self.send_message(
            session,
            recipients,
            original.message_text,
            original.message_type,
            original.frequency,
            original.baud_rate,
        )

    def _validate_inputs(self, recipients: List[str], message_text: str, message_type: str) -> None:
        if message_type not in {"alphanumeric", "numeric"}:
            raise ValueError("message_type must be 'alphanumeric' or 'numeric'")
        for ric in recipients:
            if not validate_ric_format(ric):
                raise ValueError("RIC must be a 7-digit numeric string")
        if not validate_message_length(message_text, message_type):
            raise ValueError("Message exceeds allowed length")
        if not validate_message_content(message_text, message_type):
            raise ValueError("Message contains invalid characters for its type")

    def _normalize_recipients(self, recipients: List[str | Any]) -> List[str]:
        normalized: List[str] = []
        for r in recipients:
            if isinstance(r, str):
                normalized.append(r)
            elif isinstance(r, dict) and "ric" in r:
                normalized.append(str(r["ric"]))
        if not normalized:
            raise ValueError("At least one recipient is required")
        return normalized
