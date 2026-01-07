"""Analytics service for messaging metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pisag.models import Message, MessageRecipient, Pager
from pisag.utils.query_helpers import get_analytics_summary


class AnalyticsService:
    def get_statistics(self, session: Session) -> Dict[str, Any]:
        summary = get_analytics_summary(session)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today = session.execute(
            select(func.count(Message.id)).where(Message.timestamp >= today_start)
        ).scalar_one()
        active_pagers = session.execute(select(func.count(Pager.id))).scalar_one()
        summary.update({
            "messages_today": messages_today,
            "active_pagers": active_pagers,
        })
        return summary

    def get_messages_over_time(self, session: Session, hours: int = 24) -> List[Dict[str, Any]]:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        bucket = func.strftime("%Y-%m-%dT%H:00:00", Message.timestamp)
        rows = session.execute(
            select(bucket.label("bucket"), func.count(Message.id)).where(Message.timestamp >= start_time).group_by("bucket")
        ).all()
        return [{"timestamp": row.bucket, "count": row[1]} for row in rows]

    def get_frequency_usage(self, session: Session) -> List[Dict[str, Any]]:
        rows = session.execute(select(Message.frequency, func.count(Message.id)).group_by(Message.frequency)).all()
        return [{"frequency": row[0], "count": row[1]} for row in rows]

    def get_pager_activity(self, session: Session) -> List[Dict[str, Any]]:
        rows = session.execute(
            select(MessageRecipient.ric_address, func.count(MessageRecipient.id)).group_by(MessageRecipient.ric_address)
        ).all()
        return [{"ric_address": row[0], "message_count": row[1]} for row in rows]
