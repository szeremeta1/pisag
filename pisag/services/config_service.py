"""Configuration service for runtime updates."""

from __future__ import annotations

from typing import Any, Dict

from pisag.config import get_config, reload_config
from pisag.models import SystemConfig
from pisag.utils.logging import get_logger
from pisag.utils.validation import (
    validate_frequency_range,
    validate_gain_range,
    validate_power_range,
)


class ConfigService:
    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def get_configuration(self, config_path: str = "config.json") -> Dict[str, Any]:
        return get_config(config_path)

    def update_configuration(self, session, updates: Dict[str, Any], config_path: str = "config.json") -> Dict[str, Any]:
        system_updates = updates.get("system", {})
        pocsag_updates = updates.get("pocsag", {})
        validated: Dict[str, tuple[Any, str]] = {}

        if "frequency" in system_updates:
            freq = float(system_updates["frequency"])
            if not validate_frequency_range(freq):
                raise ValueError("Frequency must be between 1 and 6000 MHz")
            validated["system.frequency"] = (freq, "float")

        if "transmit_power" in system_updates:
            power = float(system_updates["transmit_power"])
            if not validate_power_range(power):
                raise ValueError("Transmit power must be between 0 and 15 dBm")
            validated["system.transmit_power"] = (power, "float")

        if "if_gain" in system_updates:
            gain = float(system_updates["if_gain"])
            if not validate_gain_range(gain):
                raise ValueError("IF gain must be between 0 and 47 dB")
            validated["system.if_gain"] = (gain, "float")

        if "sample_rate" in system_updates:
            rate = float(system_updates["sample_rate"])
            if not 2.0 <= rate <= 30.0:
                raise ValueError("Sample rate must be between 2 and 30 MHz")
            validated["system.sample_rate"] = (rate, "float")

        if "baud_rate" in pocsag_updates:
            baud = int(pocsag_updates["baud_rate"])
            if baud not in {512, 1200, 2400}:
                raise ValueError("POCSAG baud rate must be 512, 1200, or 2400 baud")
            validated["pocsag.baud_rate"] = (baud, "int")

        if "invert" in pocsag_updates:
            invert = bool(pocsag_updates["invert"])
            validated["pocsag.invert"] = (invert, "bool")

        for key, (value, value_type) in validated.items():
            SystemConfig.set_config(session, key, value, value_type)

        session.commit()
        cfg = reload_config(config_path)
        self.logger.info("Configuration updated", extra={"updated": list(validated.keys())})
        return cfg

    @staticmethod
    def validate_frequency(freq: float) -> None:
        if not validate_frequency_range(freq):
            raise ValueError("Frequency must be between 1 and 6000 MHz")

    @staticmethod
    def validate_power(power: float) -> None:
        if not validate_power_range(power):
            raise ValueError("Transmit power must be between 0 and 15 dBm")

    @staticmethod
    def validate_gain(gain: float) -> None:
        if not validate_gain_range(gain):
            raise ValueError("IF gain must be between 0 and 47 dB")
