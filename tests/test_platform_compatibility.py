"""Tests for cross-platform compatibility."""

import json
import platform
import sys
import tempfile
from pathlib import Path

import pytest

from pisag.utils.platform import is_windows, is_linux, get_platform_name


def test_platform_detection():
    """Test platform detection functions."""
    # Should always return boolean
    assert isinstance(is_windows(), bool)
    assert isinstance(is_linux(), bool)
    
    # Platform name should be non-empty string
    platform_name = get_platform_name()
    assert isinstance(platform_name, str)
    assert len(platform_name) > 0
    
    # Verify at least one platform is detected
    # (unless on macOS or other unsupported platform)
    system = platform.system()
    if system == "Windows":
        assert is_windows() is True
        assert is_linux() is False
        assert "Windows" in platform_name
    elif system == "Linux":
        assert is_windows() is False
        assert is_linux() is True
        assert "Linux" in platform_name or "Raspberry" in platform_name


def test_signal_compatibility():
    """Test that signal handling works on current platform."""
    import signal
    
    # SIGINT should always be available
    assert hasattr(signal, 'SIGINT')
    
    # SIGTERM may not be available on Windows
    if sys.platform == "win32":
        # Windows should have SIGBREAK
        assert hasattr(signal, 'SIGBREAK')
    else:
        # Unix-like systems should have SIGTERM
        assert hasattr(signal, 'SIGTERM')


def test_app_can_import():
    """Test that the main application module can be imported."""
    from pisag.app import create_app
    
    # Should be able to import without errors
    assert create_app is not None
    assert callable(create_app)


def test_path_handling():
    """Test that pathlib is used for cross-platform paths."""
    from pathlib import Path
    from pisag.app import _BASE_PATH, _STATIC_PATH
    
    # Verify Path objects are used
    assert isinstance(_BASE_PATH, Path)
    assert isinstance(_STATIC_PATH, Path)
    
    # Paths should be absolute
    assert _BASE_PATH.is_absolute()
    assert _STATIC_PATH.is_absolute()


def test_gr_pocsag_python_binary():
    """Test that gr_pocsag encoder uses correct Python binary name."""
    from pisag.plugins.encoders.gr_pocsag import GrPocsagEncoder
    
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_data = {
            "system": {
                "frequency": 439.9875,
                "transmit_power": 10,
                "if_gain": 40,
                "sample_rate": 12.0,
                "database_path": "pisag.db"
            },
            "pocsag": {
                "baud_rate": 1200,
                "deviation": 4.5,
                "invert": False
            },
            "gr_pocsag": {
                "script_path": "EXTERNAL/gr-pocsag-master/pocsag_sender.py",
                "use_subprocess": True,
                "dry_run": True
            },
            "plugins": {
                "pocsag_encoder": "pisag.plugins.encoders.gr_pocsag.GrPocsagEncoder",
                "sdr_interface": "pisag.plugins.sdr.noop.NoopSDRInterface"
            }
        }
        config_path.write_text(json.dumps(config_data))
        
        # Create dummy script file
        script_path = Path(tmpdir) / "EXTERNAL" / "gr-pocsag-master"
        script_path.mkdir(parents=True, exist_ok=True)
        (script_path / "pocsag_sender.py").write_text("# dummy")
        
        # Update config to use dummy script
        config_data["gr_pocsag"]["script_path"] = str(script_path / "pocsag_sender.py")
        config_path.write_text(json.dumps(config_data))
        
        # Initialize encoder
        encoder = GrPocsagEncoder(config_path=str(config_path))
        
        # Check python binary name
        if sys.platform == "win32":
            assert encoder.python_bin == "python"
        else:
            assert encoder.python_bin == "python3"
