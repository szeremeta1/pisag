"""Validation helpers for pager messaging inputs."""

from __future__ import annotations

import re
from typing import Any


def validate_ric_format(ric: str) -> bool:
    return bool(re.fullmatch(r"\d{7}", ric))


def validate_message_length(text: str, message_type: str) -> bool:
    if message_type == "alphanumeric":
        return len(text) <= 80
    return True


def validate_frequency_range(freq: float) -> bool:
    return 1.0 <= freq <= 6000.0


def validate_power_range(power: float) -> bool:
    return 0.0 <= power <= 15.0


def validate_gain_range(gain: float) -> bool:
    return 0.0 <= gain <= 47.0


def sanitize_message_text(text: str, message_type: str) -> str:
    if message_type == "numeric":
        return "".join(ch for ch in text if ch.isdigit() or ch == " ")
    return "".join(ch for ch in text if 0x20 <= ord(ch) <= 0x7E)


def validate_message_content(text: str, message_type: str) -> bool:
    if message_type == "numeric":
        return all(ch.isdigit() or ch == " " for ch in text)
    return all(0x20 <= ord(ch) <= 0x7E for ch in text)
