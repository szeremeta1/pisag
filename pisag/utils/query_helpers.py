"""Common ORM query helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from pisag.models import Message, MessageRecipient


def get_message_with_recipients(session: Session, message_id: int) -> Message | None:
    stmt = (
        select(Message)
        .options(selectinload(Message.recipients).selectinload(MessageRecipient.pager))
        .where(Message.id == message_id)
    )
    return session.execute(stmt).scalar_one_or_none()


def get_analytics_summary(session: Session) -> Dict[str, Any]:
    total = session.execute(select(func.count(Message.id))).scalar_one()
    success = session.execute(select(func.count(Message.id)).where(Message.status == "success")).scalar_one()
    avg_duration = session.execute(select(func.avg(Message.duration))).scalar_one()
    return {
        "total_messages": total,
        "success_rate": float(success) / float(total) if total else 0.0,
        "average_duration": float(avg_duration) if avg_duration is not None else None,
    }


def get_messages_by_date_range(session: Session, start_date: datetime, end_date: datetime) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.timestamp.between(start_date, end_date))
        .order_by(Message.timestamp.desc())
    )
    return session.execute(stmt).scalars().all()


def get_pager_activity(session: Session, pager_id: int) -> int:
    stmt = (
        select(func.count(MessageRecipient.id))
        .where(MessageRecipient.pager_id == pager_id)
    )
    return int(session.execute(stmt).scalar_one())
