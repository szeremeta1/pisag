#!/usr/bin/env python3
"""Run this script to populate the database with sample data for development and testing."""

from __future__ import annotations

from sqlalchemy import select

from pisag.config import get_config
from pisag.models import Pager, SystemConfig, get_db_session, init_db


def seed_pagers(session) -> None:
    seeds = [
        ("Workshop Pager", "0012345", "Default workshop unit"),
        ("Test Pager 1", "0067890", "QA device"),
        ("Test Pager 2", "0011111", "Secondary QA"),
        ("Operations", "0022222", "Ops channel"),
        ("Maintenance", "0033333", "Maintenance crew"),
    ]
    existing = {p.ric_address for p in session.execute(select(Pager)).scalars()}
    for name, ric, notes in seeds:
        if ric in existing:
            continue
        session.add(Pager(name=name, ric_address=ric, notes=notes))


def seed_system_config(session) -> None:
    defaults = get_config()
    system = defaults.get("system", {})
    entries = [
        ("system.frequency", system.get("frequency", 439.9875), "float"),
        ("system.transmit_power", system.get("transmit_power", 10), "int"),
        ("system.if_gain", system.get("if_gain", 40), "int"),
        ("system.sample_rate", system.get("sample_rate", 12.0), "float"),
        ("pocsag.baud_rate", defaults.get("pocsag", {}).get("baud_rate", 512), "int"),
    ]
    for key, value, value_type in entries:
        SystemConfig.set_config(session, key, value, value_type)


def main() -> None:
    init_db()
    with get_db_session() as session:
        seed_pagers(session)
        seed_system_config(session)


if __name__ == "__main__":
    main()
