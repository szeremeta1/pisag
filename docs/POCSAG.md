# POCSAG Protocol Primer

## Overview
POCSAG (Post Office Code Standardisation Advisory Group) is a classic pager protocol from the 1980s—simple, robust, and widely adopted. PISAG implements a pure-Python encoder for educational purposes.

## Key Concepts
- **RIC Address**: 21-bit Receiver Identity Code (0–2,097,151).
- **Baud Rates**: Commonly 512, 1200, 2400 bps (PISAG uses 512 bps).
- **Message Types**: Numeric (BCD digits) and Alphanumeric (7-bit ASCII).
- **Frequencies**: Typically VHF (138–174 MHz) or UHF (400–512 MHz), region-specific.

## Transmission Structure
- **Preamble**: 576 bits of alternating 1/0 for receiver sync.
- **Sync Codeword**: 0x7CD215D8 marks the start of each batch.
- **Batch**: 16 codewords in 8 frames (2 per frame).
- **Frame Assignment**: Frame = RIC & 0x7.
- **Codeword Types**: Address, message, idle.

## Codeword Layout (32 bits)
- Data (21 bits): Address/function flag or message payload bits.
- BCH parity (10 bits): BCH(31,21) for up to 2-bit correction.
- Even parity (1 bit): Overall parity.

## BCH Error Correction
BCH(31,21) polynomial 0x769 used for parity; implemented via polynomial division in [pisag/plugins/encoders/pure_python.py](../pisag/plugins/encoders/pure_python.py).

## Message Encoding
- **Alphanumeric**: 7-bit ASCII packed into 20-bit blocks, padded with spaces.
- **Numeric**: 4-bit BCD digits (0-9, space, U, -, [, ]) packed into 20-bit blocks.

## Modulation
2-FSK with ±4.5 kHz deviation; bit 1 = +deviation, bit 0 = -deviation. Implemented in `_modulate_fsk` in the pure Python encoder.

### FSK Polarity
The POCSAG standard traditionally specifies bit 1 = mark (lower frequency) and bit 0 = space (higher frequency). However, many modern decoders including **PDW Paging Decoder** used with RTL-SDR expect the opposite polarity: bit 1 = higher frequency, bit 0 = lower frequency.

PISAG defaults to **inverted FSK polarity** (`invert: true` in config) to ensure compatibility with PDW and similar software. This can be toggled in the Settings tab of the Web UI or in the configuration file if you need to match a specific receiver's expectations.

## Resources
- POCSAG specs and amateur radio paging references
- GNU Radio examples (gr-pocsag, gr-mixalot)
- SDR tutorials and licensing guides
