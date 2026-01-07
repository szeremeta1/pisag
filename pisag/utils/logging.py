"""Centralized logging setup for the PISAG project."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "pisag.log"
_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
_CONSOLE_ENABLED = os.getenv("PISAG_CONSOLE_LOG", "1").lower() not in {"0", "false", "no"}
_LOG_LEVEL_NAME = os.getenv("PISAG_LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)
_configured = False


def _ensure_log_dir() -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _build_file_handler() -> RotatingFileHandler:
    handler = RotatingFileHandler(
        _LOG_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
    return handler


def _build_console_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
    return handler


def _configure_root(level: Optional[int] = None) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _ensure_log_dir()
    root = logging.getLogger()
    root.setLevel(level if level is not None else _LOG_LEVEL)
    root.addHandler(_build_file_handler())
    if _CONSOLE_ENABLED:
        root.addHandler(_build_console_handler())


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with rotating file and optional console handlers."""
    _configure_root()
    return logging.getLogger(name)
