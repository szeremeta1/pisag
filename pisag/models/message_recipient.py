"""MessageRecipient model definition."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from pisag.models.base import Base


class MessageRecipient(Base):
    __tablename__ = "message_recipients"
    __table_args__ = (
        Index("idx_recipients_message", "message_id"),
        Index("idx_recipients_pager", "pager_id"),
    )

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    pager_id = Column(Integer, ForeignKey("pagers.id", ondelete="SET NULL"), nullable=True)
    ric_address = Column(String(20), nullable=False)

    message = relationship("Message", back_populates="recipients")
    pager = relationship("Pager", back_populates="recipients")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<MessageRecipient id={self.id} message_id={self.message_id} ric={self.ric_address}>"
