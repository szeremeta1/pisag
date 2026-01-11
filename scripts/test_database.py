#!/usr/bin/env python3
"""Simple database smoke tests for PISAG models and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from sqlalchemy import text

from pisag.models import (
    Message,
    MessageRecipient,
    Pager,
    SystemConfig,
    TransmissionLog,
    get_db_session,
    init_db,
)
from pisag.config import reload_config


@pytest.fixture
def session(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg = {
        "system": {"database_path": str(tmp_path / "test.db")},
        "plugins": {
            "pocsag_encoder": "pisag.plugins.encoders.gr_pocsag.GrPocsagEncoder",
            "sdr_interface": "pisag.plugins.sdr.noop.NoopSDRInterface",
        },
    }
    cfg_path.write_text(json.dumps(cfg))
    reload_config(str(cfg_path))
    init_db(str(cfg_path))
    with get_db_session(str(cfg_path)) as db_session:
        yield db_session


def test_create_pager(session) -> None:
    pager = Pager(name="Test Pager", ric_address="0099999", notes="Temp")
    session.add(pager)
    session.flush()
    assert pager.id is not None


def test_create_message(session) -> None:
    message = Message(
        message_text="Hello world",
        message_type="alphanumeric",
        status="queued",
        frequency=439.9875,
        baud_rate=512,
    )
    session.add(message)
    session.flush()
    assert message.id is not None


def test_relationships(session) -> None:
    pager = Pager(name="Rel Pager", ric_address="0012121")
    session.add(pager)
    session.flush()

    message = Message(
        message_text="Test",
        message_type="numeric",
        status="encoding",
        frequency=440.0,
        baud_rate=512,
    )
    session.add(message)
    session.flush()

    recipient = MessageRecipient(message_id=message.id, pager_id=pager.id, ric_address=pager.ric_address)
    session.add(recipient)
    log = TransmissionLog(message_id=message.id, stage="queued", details="Queued for send")
    session.add(log)

    session.flush()
    assert recipient.message_id == message.id
    assert log.message_id == message.id


def test_query_helpers(session) -> None:
    now = datetime.now(timezone.utc)
    # Ensure at least one message in range
    message = Message(
        message_text="Range test",
        message_type="alphanumeric",
        status="success",
        frequency=439.0,
        baud_rate=512,
        timestamp=now,
        duration=1.2,
    )
    session.add(message)
    session.flush()

    recent = Message.get_recent(session, limit=5)
    assert message in recent

    history = Message.get_history(session, offset=0, limit=5)
    assert message in history

    status_filtered = Message.get_by_status(session, "success")
    assert any(m.id == message.id for m in status_filtered)

    TransmissionLog.get_for_message(session, message.id)


def test_indexes(session) -> None:
    idx_list = session.execute(text("PRAGMA index_list('pagers')")).all()
    assert any("idx_pagers_ric" in row for row in idx_list)


def run_all_tests() -> None:
    init_db()
    with get_db_session() as session:
        test_create_pager(session)
        test_create_message(session)
        test_relationships(session)
        test_query_helpers(session)
        test_indexes(session)
    print("All database tests passed.")


if __name__ == "__main__":
    run_all_tests()
