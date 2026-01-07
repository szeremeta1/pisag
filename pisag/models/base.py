"""SQLAlchemy base and session utilities for PISAG."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, scoped_session, sessionmaker

from pisag.config import get_config

Base = declarative_base()

_engine_cache = {}
_session_factory_cache = {}


def _normalize_db_path(db_path: str | Path) -> Path:
    return Path(db_path).expanduser().resolve()


def get_engine(config_path: str = "config.json"):
    cfg = get_config(config_path)
    db_path = _normalize_db_path(cfg.get("system", {}).get("database_path", "pisag.db"))
    key = str(db_path)
    if key not in _engine_cache:
        _engine_cache[key] = create_engine(f"sqlite:///{db_path}", future=True)
    return _engine_cache[key]


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    key = str(engine.url)
    if key not in _session_factory_cache:
        _session_factory_cache[key] = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _session_factory_cache[key]


def get_scoped_session(config_path: str = "config.json"):
    engine = get_engine(config_path)
    factory = get_session_factory(engine)
    return scoped_session(factory)


def init_db(config_path: str = "config.json") -> None:
    engine = get_engine(config_path)
    Base.metadata.create_all(engine)


@contextmanager
def get_db_session(config_path: str = "config.json") -> Generator[Session, None, None]:
    factory = get_session_factory(get_engine(config_path))
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
