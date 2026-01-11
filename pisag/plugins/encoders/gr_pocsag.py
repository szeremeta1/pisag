"""gr-pocsag integration for HackRF transmissions via GNU Radio."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import List

from pisag.config import get_config
from pisag.plugins.base import EncodingError, POCSAGEncoder, TransmissionError
from pisag.utils.logging import get_logger


class GrPocsagEncoder(POCSAGEncoder):
    """Uses the bundled gr-pocsag flowgraph to encode and transmit messages."""

    def __init__(self, config_path: str = "config.json") -> None:
        cfg = get_config(config_path)
        self.logger = get_logger(__name__)
        self.config_path = config_path
        self.system_cfg = cfg.get("system", {})
        self.pocsag_cfg = cfg.get("pocsag", {})
        self.gr_cfg = cfg.get("gr_pocsag", {})

        script = self.gr_cfg.get("script_path", "EXTERNAL/gr-pocsag-master/pocsag_sender.py")
        self.script_path = Path(script).expanduser().resolve()
        self.use_subprocess = bool(self.gr_cfg.get("use_subprocess", True))
        self.dry_run = bool(self.gr_cfg.get("dry_run", False) or os.getenv("PISAG_GR_POCSAG_DRY_RUN"))
        self.subric = int(self.gr_cfg.get("subric", 0))
        self.af_gain = float(self.gr_cfg.get("af_gain", 190))
        self.max_deviation = float(self.gr_cfg.get("max_deviation", 4500.0))
        self.symrate = int(self.gr_cfg.get("symrate", 38400))
        self.sample_rate = int(self.gr_cfg.get("sample_rate", 12000000))

    def encode(self, ric: str, message: str, message_type: str, baud_rate: int):
        raise EncodingError("GrPocsagEncoder relies on encode_and_transmit, not encode()")

    # Public API -----------------------------------------------------------
    def encode_and_transmit(
        self,
        ric: str,
        message: str,
        message_type: str,
        baud_rate: int,
        frequency_mhz: float,
        gain_db: float,
        power_dbm: float,
    ) -> None:
        self._validate_inputs(ric, message, message_type, baud_rate)
        cmd = self._build_command(ric, message, baud_rate, frequency_mhz, gain_db)
        env = os.environ.copy()
        env.update(
            {
                "PISAG_GR_POCSAG_SAMPLE_RATE": str(self.sample_rate),
                "PISAG_GR_POCSAG_AF_GAIN": str(self.af_gain),
                "PISAG_GR_POCSAG_MAX_DEVIATION": str(self.max_deviation),
                "PISAG_GR_POCSAG_SYMRATE": str(self.symrate),
                "PISAG_GR_POCSAG_POWER": str(power_dbm),
            }
        )

        self.logger.info(
            "Invoking gr-pocsag transmission",
            extra={
                "command": " ".join(map(shlex.quote, cmd)),
                "dry_run": self.dry_run,
                "frequency_mhz": frequency_mhz,
                "baud_rate": baud_rate,
                "gain_db": gain_db,
            },
        )

        if self.dry_run:
            self.logger.info("gr-pocsag dry-run enabled; skipping subprocess execution")
            return

        try:
            subprocess.run(cmd, check=True, env=env)
        except FileNotFoundError as exc:
            raise TransmissionError(f"gr-pocsag script not found at {self.script_path}") from exc
        except subprocess.CalledProcessError as exc:  # pragma: no cover - requires GNU Radio runtime
            raise TransmissionError(f"gr-pocsag failed: {exc}") from exc

    # Helpers --------------------------------------------------------------
    def _build_command(
        self, ric: str, message: str, baud_rate: int, frequency_mhz: float, gain_db: float
    ) -> List[str]:
        script = str(self.script_path)
        return [
            os.getenv("PISAG_PYTHON", "python3"),
            script,
            "--RIC",
            str(int(ric)),
            "--SubRIC",
            str(int(self.subric)),
            "--Text",
            message,
            "--Frequency",
            str(frequency_mhz),
            "--Bitrate",
            str(int(baud_rate)),
            "--TXGain",
            str(float(gain_db)),
        ]

    def _validate_inputs(self, ric: str, message: str, message_type: str, baud_rate: int) -> None:
        if not isinstance(ric, str) or not ric.isdigit() or not (1 <= len(ric) <= 7):
            raise ValueError("RIC must be a digit string of length 1-7")
        if message_type not in {"alphanumeric", "numeric"}:
            raise ValueError("message_type must be 'alphanumeric' or 'numeric'")
        if baud_rate not in {512, 1200, 2400}:
            raise ValueError("POCSAG baud rate must be 512, 1200, or 2400")
        if not message:
            raise ValueError("Message text is required")
