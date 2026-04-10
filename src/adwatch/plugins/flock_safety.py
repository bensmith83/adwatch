"""Flock Safety surveillance camera/device BLE advertisement parser.

Detects Flock Safety ALPR cameras, Penguin battery packs, and related
surveillance hardware by matching the XUNTONG (0x09C8) BLE manufacturer
company ID used in their BLE advertisements.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

XUNTONG_COMPANY_ID = 0x09C8

# Known Flock Safety BLE device OUI prefixes (MAC address first 3 octets)
FLOCK_BLE_OUIS = frozenset({
    "EC:1B:BD",
    "58:8E:81",
    "90:35:EA",
    "CC:CC:CC",
    "B4:E3:F9",
    "04:0D:84",
    "F0:82:C0",
})

# Device name patterns for classification
_NAME_PATTERNS = [
    (re.compile(r"FS Ext Battery", re.IGNORECASE), "ext_battery"),
    (re.compile(r"Penguin", re.IGNORECASE), "penguin"),
    (re.compile(r"Pigvision", re.IGNORECASE), "pigvision"),
    (re.compile(r"Flock", re.IGNORECASE), "flock"),
]


def _classify_device(local_name: str | None) -> str:
    if not local_name:
        return "unknown"
    for pattern, device_type in _NAME_PATTERNS:
        if pattern.search(local_name):
            return device_type
    return "unknown"


def _is_known_oui(mac_address: str) -> bool:
    prefix = mac_address[:8].upper()
    return prefix in FLOCK_BLE_OUIS


@register_parser(
    name="flock_safety",
    company_id=XUNTONG_COMPANY_ID,
    description="Flock Safety surveillance cameras and devices",
    version="1.0.0",
    core=False,
)
class FlockSafetyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 3:
            return None

        # Company ID is stored as first 2 bytes little-endian
        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != XUNTONG_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        device_type = _classify_device(raw.local_name)
        known_oui = _is_known_oui(raw.mac_address)

        id_hash = hashlib.sha256(
            f"flock:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata = {
            "device_type": device_type,
            "known_oui": known_oui,
            "payload_hex": payload.hex(),
        }

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="flock_safety",
            beacon_type="flock_safety",
            device_class="surveillance",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
