"""No-op SDR interface used when transmission is delegated to gr-pocsag."""

from __future__ import annotations

from pisag.plugins.base import SDRInterface
from pisag.utils.logging import get_logger


class NoopSDRInterface(SDRInterface):
    """Placeholder SDR interface for gr-pocsag-managed transmissions."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def connect(self) -> bool:
        self.logger.info("NoopSDRInterface connect invoked (gr-pocsag handles RF path)")
        return True

    def disconnect(self) -> None:
        self.logger.info("NoopSDRInterface disconnect invoked")

    def is_connected(self) -> bool:
        return True

    def configure(self, frequency: float, sample_rate: float, gain: float, power: float) -> None:
        self.logger.debug(
            "NoopSDRInterface.configure called",
            extra={"frequency": frequency, "sample_rate": sample_rate, "gain": gain, "power": power},
        )

    def transmit(self, iq_samples) -> None:
        self.logger.debug("NoopSDRInterface.transmit called - no action (handled by gr-pocsag)")
