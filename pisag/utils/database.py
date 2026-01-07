"""Flask database integration helpers."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

from flask import g

from pisag.models import get_db_session, get_session_factory

F = TypeVar("F", bound=Callable[..., Any])


def init_app_db(app) -> None:
    @app.teardown_appcontext
    def close_session(exception):  # noqa: ANN001
        session = g.pop("db_session", None)
        if session is not None:
            session.close()


def get_request_session():
    if "db_session" not in g:
        factory = get_session_factory()
        g.db_session = factory()
    return g.db_session


def with_db_session(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_db_session() as session:
            kwargs.setdefault("session", session)
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
