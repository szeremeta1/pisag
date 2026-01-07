"""TransmissionLog model definition."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, select
from sqlalchemy.orm import relationship, validates, Session

from pisag.models.base import Base


class TransmissionLog(Base):
    __tablename__ = "transmission_logs"
    __table_args__ = (
        Index("idx_logs_message", "message_id"),
        Index("idx_logs_timestamp", "timestamp", postgresql_ops={"timestamp": "DESC"}),
    )

    VALID_STAGES = {"queued", "encoding", "transmitting", "complete", "error"}

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)

    message = relationship("Message", back_populates="transmission_logs")

    @validates("stage")
    def validate_stage(self, key, value):  # noqa: D401, ANN001
        if value not in self.VALID_STAGES:
            raise ValueError(f"Invalid stage: {value}")
        return value

    @classmethod
    def get_for_message(cls, session: Session, message_id: int) -> list["TransmissionLog"]:
        stmt = select(cls).where(cls.message_id == message_id).order_by(cls.timestamp.desc())
        return session.execute(stmt).scalars().all()
