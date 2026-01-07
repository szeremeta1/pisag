"""System configuration key-value store model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, select
from sqlalchemy.orm import Session

from pisag.models.base import Base


class SystemConfig(Base):
    __tablename__ = "system_config"
    __table_args__ = (Index("idx_config_key", "key", unique=True),)

    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_typed_value(self) -> Any:
        if self.value_type == "int":
            return int(self.value)
        if self.value_type == "float":
            return float(self.value)
        if self.value_type == "bool":
            return self.value.lower() in {"1", "true", "yes"}
        return self.value

    def set_value(self, raw_value: Any, value_type: str) -> None:
        self.value_type = value_type
        if value_type == "int":
            self.value = str(int(raw_value))
        elif value_type == "float":
            self.value = str(float(raw_value))
        elif value_type == "bool":
            self.value = "1" if bool(raw_value) else "0"
        else:
            self.value = str(raw_value)

    @classmethod
    def get_by_key(cls, session: Session, key: str) -> "SystemConfig | None":
        return session.execute(select(cls).where(cls.key == key)).scalar_one_or_none()

    @classmethod
    def set_config(
        cls,
        session: Session,
        key: str,
        value: Any,
        value_type: str,
        namespace: str | None = None,
    ) -> "SystemConfig":
        dotted_key = key if "." in key or not namespace else f"{namespace}.{key}"
        record = cls.get_by_key(session, dotted_key)
        if record is None:
            record = cls(key=dotted_key, value_type=value_type, value=str(value))
            session.add(record)
        record.set_value(value, value_type)
        return record
