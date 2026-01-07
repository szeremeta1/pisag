"""Message model definition."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, select
from sqlalchemy.orm import relationship, validates, Session

from pisag.models.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_timestamp", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_messages_status", "status"),
    )

    VALID_TYPES = {"alphanumeric", "numeric"}
    VALID_STATUS = {"queued", "encoding", "transmitting", "success", "failed"}

    id = Column(Integer, primary_key=True)
    message_text = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False)
    frequency = Column(Float, nullable=False)
    baud_rate = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    recipients = relationship("MessageRecipient", back_populates="message", cascade="all, delete-orphan")
    transmission_logs = relationship("TransmissionLog", back_populates="message", cascade="all, delete-orphan")

    @validates("message_type")
    def validate_message_type(self, key, value):  # noqa: D401, ANN001
        if value not in self.VALID_TYPES:
            raise ValueError(f"Invalid message_type: {value}")
        return value

    @validates("status")
    def validate_status(self, key, value):  # noqa: D401, ANN001
        if value not in self.VALID_STATUS:
            raise ValueError(f"Invalid status: {value}")
        return value

    @classmethod
    def get_recent(cls, session: Session, limit: int = 10) -> list["Message"]:
        stmt = select(cls).order_by(cls.timestamp.desc()).limit(limit)
        return session.execute(stmt).scalars().all()

    @classmethod
    def get_by_status(cls, session: Session, status: str) -> list["Message"]:
        stmt = select(cls).where(cls.status == status).order_by(cls.timestamp.desc())
        return session.execute(stmt).scalars().all()

    @classmethod
    def get_history(cls, session: Session, offset: int = 0, limit: int = 50) -> list["Message"]:
        stmt = select(cls).order_by(cls.timestamp.desc()).offset(offset).limit(limit)
        return session.execute(stmt).scalars().all()
