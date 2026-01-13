"""Pure Python POCSAG encoder with educational commentary.

This module implements the POCSAG protocol end-to-end in Python:

- Input validation for RIC addressing, message content, and baud rate
- BCH(31,21) forward error correction with even parity
- Address and message codeword construction with LSB-first bit ordering
- Preamble and batch framing with idle fill codewords
- 2-FSK modulation to complex IQ samples for transmission

The implementation favors readability and learning value over micro-optimizations
while still using precomputed constants and vectorized NumPy operations where
useful. See the `encode` docstring for a walkthrough of the full pipeline.

IMPORTANT: Alphanumeric and numeric messages are encoded LSB-first per the POCSAG
standard (ITU-R M.584), ensuring compatibility with PDW Paging Decoder and other
standard POCSAG receivers.

This encoder supports the Motorola ADVISOR II™ POCSAG Alpha-numeric Pager
(model A05DTS5962AA) operating at 929-932 MHz with 512, 1200, or 2400 baud rates.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np

from pisag.config import SUPPORTED_POCSAG_BAUD, get_config
from pisag.plugins.base import EncodingError, POCSAGEncoder
from pisag.utils.logging import get_logger


class PurePythonEncoder(POCSAGEncoder):
    """Pure Python implementation of the POCSAG encoder.

    The encoder builds a full POCSAG transmission consisting of:
    1) 576-bit preamble (0xAAAAAAAA pattern)
    2) Two-frame batch (16 codewords) containing address and message codewords
    3) Idle fill for unused codeword slots
    4) 2-FSK IQ modulation at the configured sample rate and deviation

    Args:
        None. Configuration is loaded at construction time.

    Raises:
        EncodingError: When validation or encoding fails.
    """

    _BCH_GENERATOR = 0x769  # Generator polynomial for BCH(31,21)
    _IDLE_CODEWORD = 0x7A89C197  # Standard POCSAG idle codeword
    _PREAMBLE_WORD = 0xAAAAAAAA  # 1010... pattern

    def __init__(self, config_path: str = "config.json") -> None:
        cfg = get_config(config_path)
        system_cfg = cfg.get("system", {})
        pocsag_cfg = cfg.get("pocsag", {})
        self.sample_rate_hz = float(system_cfg.get("sample_rate", 12.0)) * 1_000_000.0
        self.deviation_hz = float(pocsag_cfg.get("deviation", 4.5)) * 1_000.0
        self.invert_fsk = bool(pocsag_cfg.get("invert", False))
        self.logger = get_logger(__name__)

    # Public API -----------------------------------------------------------
    def encode(self, ric: str, message: str, message_type: str, baud_rate: int) -> np.ndarray:
        """Encode a message into POCSAG IQ samples.

        Args:
            ric: 1-7 digit receiver identifier (RIC).
            message: Message text to transmit.
            message_type: "alphanumeric" (7-bit ASCII) or "numeric" (BCD).
            baud_rate: POCSAG baud rate (512, 1200, or 2400). Default is 1200 for
                Motorola ADVISOR II™ compatibility.

        Returns:
            Complex IQ samples (np.complex64) representing the modulated signal.

        Raises:
            ValueError: If inputs are invalid (RIC format, message content, baud rate).
            EncodingError: If encoding fails for any other reason.
        """
        try:
            self._validate_inputs(ric, message, message_type, baud_rate)
            ric_int = int(ric)

            self.logger.info(
                "  ⚙ Encoding POCSAG message",
                extra={"ric": ric, "type": message_type, "baud": baud_rate, "message_length": len(message)},
            )
            self.logger.info(f"    RIC: {ric} (decimal: {ric_int})")
            self.logger.info(f"    Type: {message_type}")
            self.logger.info(f"    Baud: {baud_rate}")
            self.logger.info(f"    Message: {repr(message)}")

            address_cw = self._generate_address_codeword(ric_int)
            msg_codewords = (
                self._encode_alphanumeric(message)
                if message_type == "alphanumeric"
                else self._encode_numeric(message)
            )
            batch_codewords = self._generate_batch(ric_int, address_cw, msg_codewords)
            bitstream = self._codewords_to_bits(batch_codewords)
            samples = self._modulate_fsk(bitstream, baud_rate)

            self.logger.info(
                "  ✓ Encoding complete",
                extra={
                    "sample_count": samples.size,
                    "duration_s": round(samples.size / self.sample_rate_hz, 3),
                    "codewords": len(batch_codewords),
                    "sample_type": str(samples.dtype),
                },
            )
            self.logger.info(f"    Generated {samples.size} samples ({samples.size / self.sample_rate_hz:.3f}s @ {self.sample_rate_hz/1e6:.1f} MHz)")
            return samples
        except Exception as exc:  # pragma: no cover - passthrough
            self.logger.error("POCSAG encoding failed", exc_info=True)
            raise EncodingError(str(exc)) from exc

    # Validation -----------------------------------------------------------
    def _validate_inputs(self, ric: str, message: str, message_type: str, baud_rate: int) -> None:
        if not isinstance(ric, str) or not ric.isdigit() or not (1 <= len(ric) <= 7):
            raise ValueError("RIC must be a digit string of length 1-7")
        ric_int = int(ric)
        if not (0 <= ric_int <= 2_097_151):  # 2^21 - 1
            raise ValueError("RIC out of range (0 to 2,097,151)")

        if message_type not in {"alphanumeric", "numeric"}:
            raise ValueError("message_type must be 'alphanumeric' or 'numeric'")

        if baud_rate not in SUPPORTED_POCSAG_BAUD:
            raise ValueError(f"POCSAG baud rate must be one of {SUPPORTED_POCSAG_BAUD}")

        if message_type == "alphanumeric":
            for ch in message:
                if not (0x20 <= ord(ch) <= 0x7E):
                    raise ValueError("Alphanumeric messages must use printable ASCII (0x20-0x7E)")
        else:
            allowed = set("0123456789U-[] ")
            if any(ch not in allowed for ch in message):
                raise ValueError("Numeric messages may contain digits, space, U, -, [, ]")

        if len(message) > 80:
            self.logger.warning("Message length exceeds 80 characters; paging systems may truncate")

    # BCH and parity -------------------------------------------------------
    def _calculate_bch_parity(self, data: int, data_bits: int) -> int:
        """Compute BCH(31,21) parity bits using polynomial division."""
        reg = data << 10  # leave room for 10 parity bits
        for i in range(data_bits - 1, -1, -1):
            if reg & (1 << (i + 10)):
                reg ^= self._BCH_GENERATOR << i
        return reg & 0x3FF  # 10 bits

    def _calculate_even_parity(self, codeword_31: int) -> int:
        """Return 1 if bitcount is odd, else 0, to achieve even parity."""
        return bin(codeword_31).count("1") & 1

    # Codeword construction ------------------------------------------------
    def _generate_address_codeword(self, ric: int) -> int:
        address = (ric >> 3) & 0x3FFFF  # 18-bit address (RIC // 8)
        function = ric & 0x3  # two function bits (RIC & 0x3)
        data = (address << 3) | (function << 1) | 0  # LSB flag = 0 for address
        parity = self._calculate_bch_parity(data, 21)
        cw31 = (data << 10) | parity
        even = self._calculate_even_parity(cw31)
        codeword = cw31 | even  # Parity in bit 0, no left shift
        self.logger.debug(
            "Address codeword generated",
            extra={
                "ric": ric,
                "address": address,
                "function": function,
                "slot": (ric & 0x7) * 2,
                "codeword": hex(codeword),
            },
        )
        return codeword

    def _encode_alphanumeric(self, message: str) -> List[int]:
        bits: List[int] = []
        for ch in message:
            val = ord(ch) & 0x7F
            for shift in range(0, 7):  # LSB-first 7 bits (POCSAG standard)
                bits.append((val >> shift) & 1)

        # Pad with spaces (0x20) to align to 20-bit blocks
        while len(bits) % 20 != 0:
            for shift in range(0, 7):
                bits.append((0x20 >> shift) & 1)
                if len(bits) % 20 == 0:
                    break

        codewords: List[int] = []
        for i in range(0, len(bits), 20):
            data_block = bits[i : i + 20]
            payload = 0
            for bit in data_block:
                payload = (payload << 1) | bit
            data_val = (payload << 1) | 1  # set message flag in LSB of 21-bit word
            parity = self._calculate_bch_parity(data_val, 21)
            cw31 = (data_val << 10) | parity
            even = self._calculate_even_parity(cw31)
            codewords.append(cw31 | even)  # Parity in bit 0, no left shift

        self.logger.debug(
            "Alphanumeric message encoded",
            extra={"chars": len(message), "codewords": len(codewords)},
        )
        return codewords

    def _encode_numeric(self, message: str) -> List[int]:
        bcd_map = {
            "0": 0x0,
            "1": 0x1,
            "2": 0x2,
            "3": 0x3,
            "4": 0x4,
            "5": 0x5,
            "6": 0x6,
            "7": 0x7,
            "8": 0x8,
            "9": 0x9,
            "U": 0xA,
            "-": 0xC,
            "[": 0xD,
            "]": 0xE,
            " ": 0xB,
        }

        bits: List[int] = []
        for ch in message:
            val = bcd_map[ch]
            for shift in range(0, 4):  # 4-bit BCD, LSB-first (POCSAG standard)
                bits.append((val >> shift) & 1)

        # Pad with spaces (0xB) to align to 20-bit blocks (5 digits per block)
        while len(bits) % 20 != 0:
            for shift in range(0, 4):
                bits.append((0xB >> shift) & 1)
                if len(bits) % 20 == 0:
                    break

        codewords: List[int] = []
        for i in range(0, len(bits), 20):
            data_block = bits[i : i + 20]
            payload = 0
            for bit in data_block:
                payload = (payload << 1) | bit
            data_val = (payload << 1) | 1  # set message flag
            parity = self._calculate_bch_parity(data_val, 21)
            cw31 = (data_val << 10) | parity
            even = self._calculate_even_parity(cw31)
            codewords.append(cw31 | even)  # Parity in bit 0, no left shift

        self.logger.debug(
            "Numeric message encoded",
            extra={"digits": len(message), "codewords": len(codewords)},
        )
        return codewords

    # Batch assembly ------------------------------------------------------
    def _generate_batch(self, ric: int, address_codeword: int, message_codewords: List[int]) -> List[int]:
        """Assemble one or more POCSAG batches, allowing long messages to span batches."""

        preamble = [self._PREAMBLE_WORD] * 18  # 576 bits, sent once
        sync_word = 0x7CD215D8
        address_pos = (ric & 0x7) * 2  # Frame assignment

        remaining = list(message_codewords)
        batches: List[int] = []
        batch_count = 0

        while True:
            batches.append(sync_word)

            # Start a fresh batch filled with idle codewords
            batch_slots = [self._IDLE_CODEWORD] * 16  # 8 frames * 2 slots

            # Include the address only in the first batch; subsequent batches maximize payload
            start_idx = 0
            if batch_count == 0:
                batch_slots[address_pos] = address_codeword
                start_idx = address_pos + 1

            placed = 0
            for idx in range(start_idx, 16):
                if not remaining:
                    break
                batch_slots[idx] = remaining.pop(0)
                placed += 1

            batches.extend(batch_slots)
            batch_count += 1

            if not remaining:
                break

        self.logger.debug(
            "Batch(es) assembled",
            extra={
                "address_pos": address_pos,
                "message_codewords": len(message_codewords),
                "batches": batch_count,
            },
        )

        return preamble + batches

    # Bitstream -----------------------------------------------------------
    def _codewords_to_bits(self, codewords: List[int]) -> List[int]:
        bits: List[int] = []
        for cw in codewords:
            for shift in range(31, -1, -1):
                bits.append((cw >> shift) & 1)
        return bits

    # Modulation ----------------------------------------------------------
    def _modulate_fsk(self, bits: List[int], baud_rate: int) -> np.ndarray:
        # Use fractional samples-per-bit with error accumulation to avoid drift
        spb_float = self.sample_rate_hz / float(baud_rate)
        spb_base = int(spb_float)
        spb_err = spb_float - spb_base

        total_samples = int(round(spb_float * len(bits)))
        samples = np.empty(total_samples, dtype=np.complex64)
        phase = 0.0
        idx = 0
        two_pi_over_sr = 2.0 * math.pi / self.sample_rate_hz
        acc = 0.0

        for bit in bits:
            # Allow polarity inversion if configured
            if self.invert_fsk:
                freq = -self.deviation_hz if bit else self.deviation_hz
            else:
                freq = self.deviation_hz if bit else -self.deviation_hz

            n = spb_base
            acc += spb_err
            if acc >= 1.0:
                n += 1
                acc -= 1.0

            phase_increment = two_pi_over_sr * freq
            for _ in range(n):
                phase += phase_increment
                samples[idx] = np.exp(1j * phase)
                idx += 1

        # In rare rounding cases, idx may be off by 1; trim if necessary
        if idx != total_samples:
            samples = samples[:idx]

        return samples
