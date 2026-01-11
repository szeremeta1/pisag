"""Base plugin definitions for encoders and SDR interfaces."""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Dict, Union

import numpy as np


class PISAGError(Exception):
    """Base exception for PISAG-specific errors."""


class EncodingError(PISAGError):
    """Raised when POCSAG encoding fails."""


class ConfigurationError(PISAGError):
    """Raised when SDR configuration fails."""


class TransmissionError(PISAGError):
    """Raised when RF transmission fails."""


class POCSAGEncoder(ABC):
    """Abstract base class for POCSAG encoders."""

    @abstractmethod
    def encode(self, ric: str, message: str, message_type: str, baud_rate: int) -> np.ndarray:
        """
        Encode message to POCSAG format and generate IQ samples.

        Args:
            ric: 7-digit RIC address (e.g., "1234567")
            message: Message content (alphanumeric or numeric)
            message_type: "alphanumeric" or "numeric"
            baud_rate: POCSAG baud rate (512, 1200, or 2400)

        Returns:
            Complex numpy array of IQ samples at configured sample rate

        Raises:
            ValueError: Invalid RIC, message, or baud rate
            EncodingError: POCSAG encoding failed
        """


class SDRInterface(ABC):
    """Abstract base class for SDR hardware interfaces."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to SDR device."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from SDR device."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if SDR device is connected."""

    @abstractmethod
    def configure(self, frequency: float, sample_rate: float, gain: float, power: float) -> None:
        """Configure SDR parameters."""

    @abstractmethod
    def transmit(self, iq_samples: np.ndarray) -> None:
        """Transmit IQ samples."""


_plugin_cache: Dict[str, Union[POCSAGEncoder, SDRInterface]] = {}


def load_plugin(plugin_type: str, plugin_class: str) -> Union[POCSAGEncoder, SDRInterface]:
    """Dynamically import and instantiate a plugin class."""
    if plugin_class in _plugin_cache:
        return _plugin_cache[plugin_class]

    module_path, class_name = plugin_class.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    instance = cls()

    if plugin_type in {"pocsag_encoder", "encoder"}:
        if not isinstance(instance, POCSAGEncoder):
            raise TypeError(f"Plugin {plugin_class} must implement POCSAGEncoder")
    elif plugin_type in {"sdr_interface", "sdr"}:
        if not isinstance(instance, SDRInterface):
            raise TypeError(f"Plugin {plugin_class} must implement SDRInterface")
    else:
        raise ValueError(f"Unknown plugin type: {plugin_type}")

    _plugin_cache[plugin_class] = instance
    return instance
