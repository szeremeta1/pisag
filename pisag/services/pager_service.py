"""Pager service operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from pisag.models import Pager
from pisag.utils.logging import get_logger
from pisag.utils.validation import validate_ric_format


class PagerService:
    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def get_all_pagers(self, session: Session) -> List[Pager]:
        return Pager.get_all(session)

    def get_pager_by_id(self, session: Session, pager_id: int) -> Optional[Pager]:
        return session.get(Pager, pager_id)

    def create_pager(self, session: Session, name: str, ric_address: str, notes: str | None = None) -> Pager:
        if not validate_ric_format(ric_address):
            raise ValueError("RIC must be a 7-digit numeric string")
        if Pager.find_by_ric(session, ric_address):
            raise ValueError("RIC already exists")
        pager = Pager(name=name, ric_address=ric_address, notes=notes)
        session.add(pager)
        session.commit()
        self.logger.info("Pager created", extra={"pager_id": pager.id})
        return pager

    def update_pager(
        self,
        session: Session,
        pager_id: int,
        name: str | None = None,
        ric_address: str | None = None,
        notes: str | None = None,
    ) -> Pager:
        pager = session.get(Pager, pager_id)
        if pager is None:
            raise ValueError("Pager not found")
        if ric_address is not None:
            if not validate_ric_format(ric_address):
                raise ValueError("RIC must be a 7-digit numeric string")
            existing = Pager.find_by_ric(session, ric_address)
            if existing and existing.id != pager.id:
                raise ValueError("RIC already exists")
            pager.ric_address = ric_address
        if name is not None:
            pager.name = name
        if notes is not None:
            pager.notes = notes
        session.commit()
        self.logger.info("Pager updated", extra={"pager_id": pager.id})
        return pager

    def delete_pager(self, session: Session, pager_id: int) -> bool:
        pager = session.get(Pager, pager_id)
        if pager is None:
            raise ValueError("Pager not found")
        session.delete(pager)
        session.commit()
        self.logger.info("Pager deleted", extra={"pager_id": pager_id})
        return True

    def search_pagers(self, session: Session, query: str) -> List[Pager]:
        stmt = select(Pager).where((Pager.name.ilike(f"%{query}%")) | (Pager.ric_address.ilike(f"%{query}%")))
        return session.execute(stmt).scalars().all()
