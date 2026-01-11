"""gr-pocsag integration for HackRF transmissions via GNU Radio."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import List

from pisag.config import SUPPORTED_POCSAG_BAUD, get_config
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
        if not self.script_path.exists():
            raise EncodingError(
                f"gr-pocsag script not found at {self.script_path}. "
                "Set gr_pocsag.script_path in config.json to the pocsag_sender.py location."
            )
        self.use_subprocess = bool(self.gr_cfg.get("use_subprocess", True))
        self.handles_transmit = True
        self.python_bin = os.getenv("PISAG_PYTHON", "python3")  # override interpreter if needed
        env_dry = os.getenv("PISAG_GR_POCSAG_DRY_RUN")
        self.dry_run = bool(self.gr_cfg.get("dry_run", False))
        if env_dry is not None:
            self.dry_run = env_dry.lower() in {"1", "true", "yes"}
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
            result = subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
            return result
        except FileNotFoundError as exc:
            raise TransmissionError(
                f"gr-pocsag script not found at {self.script_path}. "
                "Verify GNU Radio is installed and update gr_pocsag.script_path."
            ) from exc
        except subprocess.CalledProcessError as exc:  # pragma: no cover - requires GNU Radio runtime
            stderr = (exc.stderr or "").strip()
            raise TransmissionError(f"gr-pocsag failed (rc={exc.returncode}): {stderr or exc}") from exc

    # Helpers --------------------------------------------------------------
    def _build_command(
        self, ric: str, message: str, baud_rate: int, frequency_mhz: float, gain_db: float
    ) -> List[str]:
        script = str(self.script_path)
        return [
            self.python_bin,
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
            str(int(round(gain_db))),  # external script requires integer gain
        ]

    def _validate_inputs(self, ric: str, message: str, message_type: str, baud_rate: int) -> None:
        if not isinstance(ric, str) or not ric.isdigit() or not (1 <= len(ric) <= 7):
            raise ValueError("RIC must be a digit string of length 1-7")
        ric_val = int(ric)
        if ric_val < 0 or ric_val > 2_097_151:
            raise ValueError("RIC out of range (0-2,097,151)")
        if message_type not in {"alphanumeric", "numeric"}:
            raise ValueError("message_type must be 'alphanumeric' or 'numeric'")
        if baud_rate not in SUPPORTED_POCSAG_BAUD:
            raise ValueError(f"POCSAG baud rate must be one of {SUPPORTED_POCSAG_BAUD}")
        if not message:
            raise ValueError("Message text is required")
