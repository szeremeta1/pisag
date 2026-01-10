# POCSAG Encoding Fix - Technical Details

## Problem Statement

Prior to this fix, PISAG was unable to transmit messages that could be received and decoded by PDW Paging Decoder or other standard POCSAG receivers using RTL-SDR. The root cause was incorrect bit ordering in the message encoding.

## Root Cause Analysis

### Background

The POCSAG protocol (ITU-R M.584) specifies precise bit ordering requirements:
- **Codewords** are transmitted MSB-first (bit 31 to bit 0)
- **Message payloads** within codewords use LSB-first encoding
- **ASCII characters** in alphanumeric messages are encoded as 7 bits, transmitted from bit 0 (LSB) to bit 6 (MSB)
- **BCD digits** in numeric messages are encoded as 4 bits, transmitted from bit 0 (LSB) to bit 3 (MSB)

### The Issue

PISAG's original implementation transmitted character and digit bits in MSB-first order:

```python
# INCORRECT (original implementation)
for shift in range(6, -1, -1):  # MSB-first
    bits.append((val >> shift) & 1)
```

This meant that the ASCII character 'H' (0x48 = 0b1001000) was transmitted as:
- **Incorrect**: 1 0 0 1 0 0 0 (MSB-first)
- **Should be**: 0 0 0 1 0 0 1 (LSB-first)

### Reference Implementations

Analysis of working POCSAG implementations confirmed the correct approach:

1. **gr-pocsag** (GNU Radio): Explicitly reverses bit order per character
   ```python
   charbits = BitArray(uint=c, length=7)
   charbits.reverse()  # Reverse to get LSB-first
   ```

2. **UniPager**: Uses LSB-first encoding throughout

3. **pagermon**: Receives and decodes messages with LSB-first expectation

## Solution

Changed both alphanumeric and numeric encoding to use LSB-first bit ordering:

### Alphanumeric Fix

```python
# CORRECT (fixed implementation)
for shift in range(0, 7):  # LSB-first (POCSAG standard)
    bits.append((val >> shift) & 1)
```

### Numeric Fix

```python
# CORRECT (fixed implementation)
for shift in range(0, 4):  # LSB-first (POCSAG standard)
    bits.append((val >> shift) & 1)
```

## Verification

The fix was verified through:

1. **Bit-level tests**: Confirmed that characters are now encoded LSB-first
   - 'H' (0x48): 0 0 0 1 0 0 1 ✓
   - '1' (BCD 0x1): 1 0 0 0 ✓

2. **Codeword generation**: Verified complete message codewords are generated correctly

3. **Reference comparison**: Output now matches gr-pocsag and other working implementations

## Impact

This fix ensures that PISAG transmissions can be:
- Received by PDW Paging Decoder with RTL-SDR
- Decoded by any standard POCSAG receiver
- Compatible with gr-pocsag, UniPager, and pagermon
- Compliant with ITU-R M.584 specification

## Additional Notes

### FSK Polarity

PISAG already had the correct FSK polarity configuration:
- `invert: true` by default in config.json
- This matches RTL-SDR/PDW expectations (bit 1 = higher frequency)

### Other Components

The following were already correct and did not require changes:
- BCH(31,21) error correction polynomial (0x769)
- Sync codeword (0x7CD215D8)
- Idle codeword (0x7A89C197)
- Preamble pattern (0xAAAAAAAA)
- Address codeword generation
- Batch and frame structure

## Testing Recommendations

To verify POCSAG transmission with PDW:

1. **Set up receiver**:
   - RTL-SDR connected to PC
   - PDW Paging Decoder configured for POCSAG 512 baud
   - Tune to transmission frequency (e.g., 439.9875 MHz)

2. **Transmit test message**:
   - Use PISAG web UI or API
   - Send simple message like "TEST" to a known RIC
   - Observe PDW for successful decode

3. **Expected result**:
   - PDW should display the RIC and decoded message text
   - Message should be readable and match what was sent

## References

- ITU-R M.584: POCSAG specification
- gr-pocsag: https://github.com/on1arf/gr-pocsag
- UniPager: https://github.com/rwth-afu/UniPager
- pagermon: https://github.com/pagermon/pagermon

## Files Modified

1. `pisag/plugins/encoders/pure_python.py`:
   - Changed alphanumeric encoding to LSB-first (line 176)
   - Changed numeric encoding to LSB-first (line 226)
   - Updated docstring to document LSB-first requirement

2. `docs/POCSAG.md`:
   - Updated message encoding section to specify LSB-first ordering

3. `docs/TROUBLESHOOTING.md`:
   - Added note about LSB-first encoding fix

4. `README.md`:
   - Enhanced PDW compatibility note to mention LSB-first encoding

## Commit

```
Fix POCSAG bit ordering: use LSB-first encoding per standard

- Changed alphanumeric encoding from MSB-first to LSB-first bit order
- Changed numeric encoding from MSB-first to LSB-first bit order
- Updated documentation to reflect correct POCSAG standard
- This fixes PDW Paging Decoder compatibility issues

The POCSAG standard (ITU-R M.584) specifies that message bits within
each character/digit should be transmitted LSB-first. Previous
implementation used MSB-first which made messages unreadable by
standard decoders like PDW.
```
