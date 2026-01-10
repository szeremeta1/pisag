# UniPager Integration Guide

This document describes the integration of UniPager's POCSAG encoding into PISAG and provides a roadmap for using UniPager as an alternative encoder.

## Background

UniPager is a mature, production-tested POCSAG transmitter controller written in Rust. It has been successfully used in real-world paging systems and implements the POCSAG protocol correctly per ITU-R M.584.

## Current Status

### Critical Bug Fixed ✓

The PurePythonEncoder had a critical bug where it was shifting the entire 31-bit codeword left by 1 bit before adding the parity bit. This corrupted all POCSAG codewords, making them undecodable.

**Fixed in commit**: Fix critical POCSAG codeword encoding bug - remove erroneous left shift

The bug was on lines 163, 200, and 250 of `pisag/plugins/encoders/pure_python.py`:
- **Before (buggy)**: `codeword = (cw31 << 1) | even`
- **After (correct)**: `codeword = cw31 | even`

This fix makes PurePythonEncoder generate codewords that exactly match UniPager's output.

## Verified Compatibility

The fixed PurePythonEncoder has been verified to produce identical codewords to UniPager:

```python
RIC: 1234567
PurePythonEncoder: 0x4b5a1a25
UniPager:          0x4b5a1a25
Match: True ✓
```

## UniPager Integration Options

### Option 1: Use Fixed PurePythonEncoder (Recommended - Done)

The PurePythonEncoder now implements the POCSAG standard correctly and produces the same output as UniPager. This is the simplest and most maintainable approach.

**Advantages:**
- No additional dependencies
- Pure Python - easy to debug and maintain
- Already integrated into PISAG's plugin system
- Matches UniPager's behavior exactly

**Status:** ✅ Complete and verified

### Option 2: Python-Rust Bridge via PyO3 (Future Enhancement)

Create a Python extension module that calls UniPager's Rust encoding functions directly.

**Implementation Path:**
1. Create a new Rust crate in `pisag/plugins/encoders/unipager_bridge/`
2. Use PyO3 to expose UniPager's encoding functions to Python
3. Wrap UniPager's `Generator` in a Python class
4. Implement the `POCSAGEncoder` interface

**Example Structure:**
```rust
// pisag/plugins/encoders/unipager_bridge/src/lib.rs
use pyo3::prelude::*;
use unipager::pocsag::{Generator, Message, MessageType};

#[pyclass]
struct UniPagerEncoder {
    // State
}

#[pymethods]
impl UniPagerEncoder {
    #[new]
    fn new() -> Self {
        UniPagerEncoder {}
    }
    
    fn encode(&self, ric: &str, message: &str, message_type: &str, baud_rate: i32) -> PyResult<Vec<u32>> {
        // Call UniPager's Generator
        // Return codewords
    }
}

#[pymodule]
fn unipager_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<UniPagerEncoder>()?;
    Ok(())
}
```

**Configuration:**
```json
{
  "plugins": {
    "pocsag_encoder": "pisag.plugins.encoders.unipager_bridge.UniPagerEncoder",
    "sdr_interface": "pisag.plugins.sdr.soapy_hackrf.SoapySDRInterface"
  }
}
```

**Advantages:**
- Direct use of battle-tested Rust implementation
- Potential performance improvements
- Automatic updates with UniPager improvements

**Disadvantages:**
- Requires Rust toolchain for building
- More complex build and deployment
- Additional dependency management

**Status:** 🔄 Future enhancement (optional)

### Option 3: ctypes FFI Bridge (Alternative)

Build UniPager as a shared library and call it via Python's ctypes.

**Implementation Path:**
1. Modify UniPager's Cargo.toml to build as cdylib
2. Create C-compatible FFI interface
3. Load and call from Python via ctypes

**Status:** 🔄 Alternative approach (if PyO3 is not feasible)

## Testing and Validation

### Test with PDW Paging Decoder

PDW (Paging Decoder for Windows) is the de facto standard for testing POCSAG transmissions.

1. Install PDW on a Windows machine
2. Set up an RTL-SDR or similar receiver
3. Configure PDW to listen on your transmission frequency (default: 439.9875 MHz)
4. Send a test message from PISAG
5. Verify that PDW decodes the message correctly

**Expected PDW Output:**
```
RIC: 1234567
Type: Alphanumeric
Message: Hello POCSAG
```

### Test with Real Pagers

If you have access to real POCSAG pagers:

1. Program a pager with the test RIC (e.g., 1234567)
2. Set the pager to the correct frequency
3. Transmit a test message from PISAG
4. Verify the pager receives and displays the message

**Important:** Ensure you have proper licensing and authorization for radio transmission.

## References

- POCSAG Standard: ITU-R M.584
- UniPager: https://github.com/rwth-afu/UniPager
- PDW Decoder: http://discriminator.nl/pdw/index-en.html
- PISAG Architecture: docs/ARCHITECTURE.md
- POCSAG Protocol: docs/POCSAG.md

## Conclusion

The critical encoding bug has been fixed, and PISAG now generates correct, standard-compliant POCSAG codewords that match UniPager's output. Messages should now be decodable by PDW Paging Decoder and real pagers.

For future enhancements, UniPager can be integrated more directly via PyO3 or ctypes, but this is optional since the fixed PurePythonEncoder already produces correct output.
