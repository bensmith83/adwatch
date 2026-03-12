"""Shared utilities for adwatch."""


def extract_company_id(hex_str: str | None) -> int | None:
    """Extract BLE company ID from little-endian manufacturer data hex string."""
    if not hex_str or len(hex_str) < 4:
        return None
    low = int(hex_str[0:2], 16)
    high = int(hex_str[2:4], 16)
    return high * 256 + low
