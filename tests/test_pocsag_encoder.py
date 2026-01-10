"""Test POCSAG encoder to verify correct codeword generation.

This test validates that the POCSAG encoder generates correct codewords
that match the POCSAG standard (ITU-R M.584) and are compatible with
standard decoders like PDW Paging Decoder.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pisag.plugins.encoders.pure_python import PurePythonEncoder
import numpy as np


def test_address_codeword_generation():
    """Test that address codewords are generated correctly."""
    encoder = PurePythonEncoder()
    
    # Test case from UniPager analysis
    ric = 1234567
    
    # Expected values based on POCSAG standard and UniPager
    expected_address = (ric >> 3) & 0x3FFFF  # 154320
    expected_function = ric & 0x3  # 3
    expected_frame_pos = (ric & 0x7) * 2  # 14
    
    # Generate address codeword
    codeword = encoder._generate_address_codeword(ric)
    
    # Expected codeword based on UniPager (verified match)
    expected_codeword = 0x4b5a1a25
    
    print(f"RIC: {ric}")
    print(f"Address: {expected_address}")
    print(f"Function: {expected_function}")
    print(f"Frame position: {expected_frame_pos}")
    print(f"Generated codeword: 0x{codeword:08x}")
    print(f"Expected codeword:  0x{expected_codeword:08x}")
    print(f"Match: {codeword == expected_codeword}")
    
    assert codeword == expected_codeword, f"Codeword mismatch: 0x{codeword:08x} != 0x{expected_codeword:08x}"
    
    # Verify parity bit (bit 0)
    bit_count = bin(codeword).count('1')
    assert bit_count % 2 == 0, f"Even parity check failed: {bit_count} bits set"
    
    print("✓ Address codeword test PASSED")


def test_alphanumeric_encoding():
    """Test alphanumeric message encoding."""
    encoder = PurePythonEncoder()
    
    message = "TEST"
    message_type = "alphanumeric"
    
    # Generate message codewords
    codewords = encoder._encode_alphanumeric(message)
    
    print(f"\nMessage: '{message}'")
    print(f"Number of codewords: {len(codewords)}")
    
    # Each codeword should have even parity
    for i, cw in enumerate(codewords):
        bit_count = bin(cw).count('1')
        print(f"Codeword {i}: 0x{cw:08x} ({bit_count} bits)")
        assert bit_count % 2 == 0, f"Even parity check failed for codeword {i}"
        
        # Verify message flag (bit 11 should be 1)
        message_flag = (cw >> 11) & 1
        assert message_flag == 1, f"Message flag not set in codeword {i}"
    
    print("✓ Alphanumeric encoding test PASSED")


def test_numeric_encoding():
    """Test numeric message encoding."""
    encoder = PurePythonEncoder()
    
    message = "12345"
    message_type = "numeric"
    
    # Generate message codewords
    codewords = encoder._encode_numeric(message)
    
    print(f"\nMessage: '{message}'")
    print(f"Number of codewords: {len(codewords)}")
    
    # Each codeword should have even parity
    for i, cw in enumerate(codewords):
        bit_count = bin(cw).count('1')
        print(f"Codeword {i}: 0x{cw:08x} ({bit_count} bits)")
        assert bit_count % 2 == 0, f"Even parity check failed for codeword {i}"
        
        # Verify message flag (bit 11 should be 1)
        message_flag = (cw >> 11) & 1
        assert message_flag == 1, f"Message flag not set in codeword {i}"
    
    print("✓ Numeric encoding test PASSED")


def test_full_encoding_pipeline():
    """Test the full encoding pipeline from RIC + message to IQ samples."""
    encoder = PurePythonEncoder()
    
    ric = "1234567"
    message = "Hello POCSAG"
    message_type = "alphanumeric"
    baud_rate = 512
    
    print(f"\nFull encoding test:")
    print(f"  RIC: {ric}")
    print(f"  Message: '{message}'")
    print(f"  Type: {message_type}")
    print(f"  Baud: {baud_rate}")
    
    # Encode message
    iq_samples = encoder.encode(ric, message, message_type, baud_rate)
    
    print(f"  Generated {len(iq_samples)} IQ samples")
    print(f"  Sample dtype: {iq_samples.dtype}")
    print(f"  Complex samples: {np.iscomplexobj(iq_samples)}")
    
    # Verify output
    assert isinstance(iq_samples, np.ndarray), "Output should be numpy array"
    assert iq_samples.dtype == np.complex64, "Output should be complex64"
    assert len(iq_samples) > 0, "Should generate samples"
    
    # Verify sample values are reasonable (magnitude should be ~1)
    magnitudes = np.abs(iq_samples)
    assert np.all(magnitudes > 0.9) and np.all(magnitudes < 1.1), "Sample magnitudes should be ~1"
    
    print("✓ Full encoding pipeline test PASSED")


def test_idle_codeword():
    """Test that idle codewords are correct."""
    encoder = PurePythonEncoder()
    expected_idle = 0x7A89C197
    
    print(f"\nIdle codeword: 0x{encoder._IDLE_CODEWORD:08x}")
    print(f"Expected:      0x{expected_idle:08x}")
    
    assert encoder._IDLE_CODEWORD == expected_idle, "Idle codeword mismatch"
    
    # Verify idle codeword has even parity
    bit_count = bin(expected_idle).count('1')
    assert bit_count % 2 == 0, "Idle codeword should have even parity"
    
    print("✓ Idle codeword test PASSED")


def test_preamble():
    """Test that preamble is correct."""
    encoder = PurePythonEncoder()
    expected_preamble = 0xAAAAAAAA
    
    print(f"\nPreamble word: 0x{encoder._PREAMBLE_WORD:08x}")
    print(f"Expected:      0x{expected_preamble:08x}")
    
    assert encoder._PREAMBLE_WORD == expected_preamble, "Preamble word mismatch"
    
    print("✓ Preamble test PASSED")


def test_bch_parity():
    """Test BCH parity calculation."""
    encoder = PurePythonEncoder()
    
    # Test with known values
    test_data = 0x12D686  # 21-bit data from RIC 1234567
    parity = encoder._calculate_bch_parity(test_data, 21)
    expected_parity = 0x224  # From earlier analysis
    
    print(f"\nBCH parity test:")
    print(f"  Data: 0x{test_data:06x}")
    print(f"  Calculated parity: 0x{parity:03x}")
    print(f"  Expected parity:   0x{expected_parity:03x}")
    
    assert parity == expected_parity, f"BCH parity mismatch: 0x{parity:03x} != 0x{expected_parity:03x}"
    
    print("✓ BCH parity test PASSED")


if __name__ == "__main__":
    print("=" * 70)
    print("POCSAG Encoder Test Suite")
    print("=" * 70)
    
    try:
        test_bch_parity()
        test_idle_codeword()
        test_preamble()
        test_address_codeword_generation()
        test_alphanumeric_encoding()
        test_numeric_encoding()
        test_full_encoding_pipeline()
        
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print("\nThe encoder now generates correct POCSAG codewords that should be")
        print("decodable by PDW Paging Decoder and compatible with real pagers.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
