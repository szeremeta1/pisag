"""SoapySDR-based SDR interface for HackRF One."""

from __future__ import annotations

import numpy as np
from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_TX, Device  # type: ignore

from pisag.plugins.base import ConfigurationError, SDRInterface, TransmissionError
from pisag.utils.logging import get_logger


class SoapySDRInterface(SDRInterface):
    """HackRF SDR interface using SoapySDR."""

    def __init__(self) -> None:
        self.device = None
        self.logger = get_logger(__name__)
        self._connected = False

    def connect(self) -> bool:
        try:
            devices = Device.enumerate({"driver": "hackrf"})
            if not devices:
                self.logger.error("No HackRF devices found via SoapySDR")
                return False
            self.device = Device(devices[0])
            self._connected = True
            self.logger.info("HackRF connected via SoapySDR")
            return True
        except RuntimeError as exc:  # pragma: no cover - hardware path
            self.logger.error("Failed to connect to HackRF", exc_info=True)
            self._connected = False
            self.device = None
            return False

    def disconnect(self) -> None:
        self.device = None
        self._connected = False
        self.logger.info("HackRF disconnected")

    def is_connected(self) -> bool:
        return self._connected and self.device is not None

    def configure(self, frequency: float, sample_rate: float, gain: float, power: float) -> None:
        if not self.is_connected():
            raise ConfigurationError("SDR not connected")
        try:
            freq_hz = frequency * 1e6
            rate_hz = sample_rate * 1e6
            self.device.setFrequency(SOAPY_SDR_TX, 0, freq_hz)
            self.device.setSampleRate(SOAPY_SDR_TX, 0, rate_hz)
            self.device.setGain(SOAPY_SDR_TX, 0, "IF", gain)
            # Apply transmit power via the PA/VGA stage when available; fallback to generic gain.
            try:
                self.device.setGain(SOAPY_SDR_TX, 0, "PA", power)
            except RuntimeError:
                try:
                    self.device.setGain(SOAPY_SDR_TX, 0, "VGA", power)
                except RuntimeError:
                    self.device.setGain(SOAPY_SDR_TX, 0, power)
            self.device.writeSetting("tx_amp_enable", "true")
            self.logger.info(
                "  ⚙ SDR configured for transmission",
                extra={
                    "frequency_mhz": frequency,
                    "sample_rate_mhz": sample_rate,
                    "if_gain_db": gain,
                    "tx_power_dbm": power,
                },
            )
            self.logger.info(f"    Frequency: {frequency} MHz ({freq_hz/1e6:.6f} MHz exact)")
            self.logger.info(f"    Sample Rate: {sample_rate} MHz ({rate_hz/1e6:.6f} MHz exact)")
            self.logger.info(f"    IF Gain: {gain} dB")
            self.logger.info(f"    TX Power: {power} dBm")
            self.logger.info(f"    TX Amp: Enabled")
        except RuntimeError as exc:  # pragma: no cover - hardware path
            self.logger.error("Failed to configure SDR", exc_info=True)
            raise ConfigurationError(str(exc))

    def transmit(self, iq_samples: np.ndarray) -> None:
        if not self.is_connected():
            raise TransmissionError("SDR not connected")
        if not isinstance(iq_samples, np.ndarray) or not np.iscomplexobj(iq_samples):
            raise TransmissionError("iq_samples must be a complex numpy array")
        try:
            stream = self.device.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
            self.device.activateStream(stream)
            samples_cf32 = iq_samples.astype(np.complex64)
            actual_sr = self.device.getSampleRate(SOAPY_SDR_TX, 0)
            actual_freq = self.device.getFrequency(SOAPY_SDR_TX, 0)
            self.logger.info(
                "  📡 Starting RF transmission",
                extra={
                    "sample_count": len(iq_samples),
                    "sample_rate_hz": actual_sr,
                    "frequency_hz": actual_freq,
                    "duration_s": len(iq_samples) / actual_sr,
                },
            )
            self.logger.info(f"    Samples: {len(iq_samples)}")
            self.logger.info(f"    Frequency: {actual_freq/1e6:.6f} MHz")
            self.logger.info(f"    Sample Rate: {actual_sr/1e6:.6f} MHz")
            self.logger.info(f"    Duration: {len(iq_samples) / actual_sr:.3f} seconds")
            self.logger.info("    ⏳ Writing samples to HackRF in chunks...")
            
            # Write samples in chunks to ensure all data is transmitted
            total_written = 0
            chunk_size = 131072  # Write in 128K chunks
            num_chunks = (len(samples_cf32) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(samples_cf32), chunk_size):
                chunk = samples_cf32[i:i + chunk_size]
                result = self.device.writeStream(stream, [chunk], len(chunk))
                if isinstance(result, tuple):
                    written = result[0]
                else:
                    written = result
                total_written += written
                if (i // chunk_size + 1) % 10 == 0 or i + chunk_size >= len(samples_cf32):
                    self.logger.info(f"      Progress: {total_written}/{len(samples_cf32)} samples ({100*total_written/len(samples_cf32):.1f}%)")
            
            self.logger.info(f"    ✓ Wrote {total_written}/{len(samples_cf32)} samples")
            self.device.deactivateStream(stream)
            self.device.closeStream(stream)
            self.logger.info("  ✓ RF transmission completed")
        except RuntimeError as exc:  # pragma: no cover - hardware path
            self.logger.error("Transmission failed", exc_info=True)
            raise TransmissionError(str(exc))
