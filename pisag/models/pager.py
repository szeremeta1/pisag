"""Pager model definition."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, select
from sqlalchemy.orm import relationship, Session

from pisag.models.base import Base


class Pager(Base):
    __tablename__ = "pagers"
    __table_args__ = (Index("idx_pagers_ric", "ric_address"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    ric_address = Column(String(20), nullable=False, unique=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipients = relationship("MessageRecipient", back_populates="pager")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<Pager id={self.id} ric={self.ric_address}>"

    @classmethod
    def find_by_ric(cls, session: Session, ric_address: str) -> "Pager | None":
        return session.execute(select(cls).where(cls.ric_address == ric_address)).scalar_one_or_none()

    @classmethod
    def get_all(cls, session: Session) -> list["Pager"]:
        return session.execute(select(cls).order_by(cls.name)).scalars().all()
