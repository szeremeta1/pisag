"""Platform detection and compatibility utilities."""

import platform
import sys


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or platform.system() == "Windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux") or platform.system() == "Linux"


def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi (Linux with ARM architecture)."""
    if not is_linux():
        return False
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
            return "BCM" in cpuinfo or "Raspberry Pi" in cpuinfo
    except Exception:
        return False


def get_platform_name() -> str:
    """Get a human-readable platform name."""
    if is_raspberry_pi():
        return "Raspberry Pi"
    elif is_windows():
        return "Windows"
    elif is_linux():
        return "Linux"
    else:
        return platform.system()
