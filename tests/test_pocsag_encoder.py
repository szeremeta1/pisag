import json
import os
from pathlib import Path

import subprocess

import pytest

from pisag.config import reload_config
from pisag.plugins.encoders.gr_pocsag import GrPocsagEncoder


def _write_config(tmp_path: Path, extra: dict | None = None) -> Path:
    base = {
        "system": {"frequency": 439.9875, "transmit_power": 10, "if_gain": 40, "sample_rate": 12.0},
        "pocsag": {"baud_rate": 1200, "deviation": 4.5, "invert": False},
        "gr_pocsag": {
            "script_path": "EXTERNAL/gr-pocsag-master/pocsag_sender.py",
            "use_subprocess": True,
            "dry_run": True,
            "subric": 0,
            "af_gain": 190,
            "max_deviation": 4500.0,
            "symrate": 38400,
            "sample_rate": 12000000,
        },
        "plugins": {
            "pocsag_encoder": "pisag.plugins.encoders.gr_pocsag.GrPocsagEncoder",
            "sdr_interface": "pisag.plugins.sdr.noop.NoopSDRInterface",
        },
        "system_config": {},
    }
    if extra:
        base.update(extra)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(base))
    reload_config(str(cfg_path))
    return cfg_path


def test_builds_gr_pocsag_command(tmp_path):
    cfg_path = _write_config(tmp_path)
    encoder = GrPocsagEncoder(config_path=str(cfg_path))
    cmd = encoder._build_command("1234567", "HELLO", 1200, 439.9875, 10)

    joined = " ".join(cmd)
    assert "pocsag_sender.py" in joined
    assert "--RIC" in cmd and "1234567" in cmd
    assert "--Frequency" in cmd and "439.9875" in cmd
    assert "--Bitrate" in cmd and "1200" in cmd
    assert "--TXGain" in cmd and "10.0" in joined


def test_encode_and_transmit_respects_dry_run(tmp_path, monkeypatch):
    cfg_path = _write_config(tmp_path)
    monkeypatch.setenv("PISAG_GR_POCSAG_DRY_RUN", "1")
    calls: list[list[str]] = []

    def fake_run(cmd, check, env):
        calls.append(cmd)
        raise AssertionError("subprocess should not be called when dry_run is enabled")

    monkeypatch.setattr(subprocess, "run", fake_run)

    encoder = GrPocsagEncoder(config_path=str(cfg_path))
    encoder.encode_and_transmit("7654321", "Test", "alphanumeric", 1200, 439.1, 20, 5)

    assert calls == []
    monkeypatch.delenv("PISAG_GR_POCSAG_DRY_RUN", raising=False)
