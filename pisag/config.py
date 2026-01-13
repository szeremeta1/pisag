"""Hybrid configuration loader for PISAG."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

SUPPORTED_POCSAG_BAUD = (512, 1200, 2400)

_DEFAULT_CONFIG: Dict[str, Any] = {
    "system": {
        "frequency": 929.6125,  # Motorola ADVISOR II™ compatible (929-932 MHz band)
        "transmit_power": 10,
        "if_gain": 40,
        "sample_rate": 12.0,
        "database_path": "pisag.db",
        "log_level": "INFO",
    },
    "pocsag": {
        "baud_rate": SUPPORTED_POCSAG_BAUD[1],
        "deviation": 4.5,
        "invert": False,
    },
    "gr_pocsag": {
        "script_path": "EXTERNAL/gr-pocsag-master/pocsag_sender.py",
        "use_subprocess": True,
        "dry_run": False,
        "subric": 0,
        "af_gain": 190,
        "max_deviation": 4500.0,
        "symrate": 38400,
        "sample_rate": 12000000,
    },
    "hackrf": {
        "device_index": 0,
        "antenna_enable": True,
    },
    "plugins": {
        "pocsag_encoder": "pisag.plugins.encoders.gr_pocsag.GrPocsagEncoder",
        "sdr_interface": "pisag.plugins.sdr.noop.NoopSDRInterface",
    },
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
    },
}

_cached_config: Dict[str, Any] | None = None
_cached_config_path: Path | None = None


class ConfigurationError(ValueError):
    """Raised when configuration validation fails."""


def load_json_config(path: str = "config.json") -> Dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        return deepcopy(_DEFAULT_CONFIG)
    with cfg_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    merged: Dict[str, Any] = deepcopy(_DEFAULT_CONFIG)
    _deep_update(merged, data)
    _require_keys(merged)
    return merged


def load_database_overrides(db_path: str | Path | None = None) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    db_path = Path(db_path) if db_path is not None else Path(_DEFAULT_CONFIG["system"]["database_path"])
    if not db_path.exists():
        return overrides
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, value_type FROM system_config")
        for key, value, value_type in cursor.fetchall():
            overrides = _apply_override(overrides, key, _deserialize_value(value, value_type))
    except sqlite3.Error:
        return {}
    finally:
        try:
            conn.close()  # type: ignore[arg-type]
        except Exception:
            pass
    return overrides


def get_config(path: str = "config.json") -> Dict[str, Any]:
    global _cached_config, _cached_config_path
    cfg_path = Path(path)
    if _cached_config is not None and _cached_config_path == cfg_path:
        return _cached_config

    defaults = load_json_config(path)
    db_path = defaults.get("system", {}).get("database_path", _DEFAULT_CONFIG["system"]["database_path"])
    overrides = load_database_overrides(db_path)
    merged = deepcopy(defaults)
    _deep_update(merged, overrides)
    _validate(merged)
    _cached_config = merged
    _cached_config_path = cfg_path
    return merged


def reload_config(path: str = "config.json") -> Dict[str, Any]:
    global _cached_config, _cached_config_path
    _cached_config = None
    _cached_config_path = None
    return get_config(path)


# Helpers

def _deep_update(target: Dict[str, Any], updates: Dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _apply_override(base: Dict[str, Any], dotted_key: str, value: Any) -> Dict[str, Any]:
    parts = dotted_key.split(".")
    cursor = base
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})  # type: ignore[assignment]
    cursor[parts[-1]] = value
    return base


def _deserialize_value(raw: str, value_type: str) -> Any:
    value_type = (value_type or "str").lower()
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "bool":
        return raw.lower() in {"1", "true", "yes"}
    if value_type == "json":
        return json.loads(raw)
    return raw


def _require_keys(cfg: Dict[str, Any]) -> None:
    required_paths = [
        ("system", "frequency"),
        ("system", "transmit_power"),
        ("system", "sample_rate"),
        ("pocsag", "baud_rate"),
    ]
    for section, key in required_paths:
        if section not in cfg or key not in cfg[section]:
            raise ConfigurationError(f"Missing required configuration key: {section}.{key}")


def _validate(cfg: Dict[str, Any]) -> None:
    freq = float(cfg["system"]["frequency"])
    if not 1.0 <= freq <= 6000.0:
        raise ConfigurationError("Frequency must be between 1 and 6000 MHz for HackRF.")

    power = float(cfg["system"]["transmit_power"])
    if not -10 <= power <= 15:
        raise ConfigurationError("Transmit power must be between -10 and 15 dBm.")

    sample_rate = float(cfg["system"]["sample_rate"])
    if not 2.0 <= sample_rate <= 30.0:
        raise ConfigurationError("Sample rate must be between 2 and 30 MHz.")

    baud_rate = int(cfg["pocsag"]["baud_rate"])
    if baud_rate not in SUPPORTED_POCSAG_BAUD:
        raise ConfigurationError(f"POCSAG baud rate must be one of {SUPPORTED_POCSAG_BAUD}.")
