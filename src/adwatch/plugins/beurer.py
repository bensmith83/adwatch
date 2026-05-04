"""Beurer HealthManager plugin (BP monitors, scales, oximeters, ECG, etc.).

Per apk-ble-hunting/reports/beurer-healthmanager_passive.md:

  - Beurer SIG company_id: 0x043A
  - 6 vendor service-UUID families:
      D0A2FF00-... (custom 128-bit, activity/BGM)
      0x6006 (BP / oximeter)
      0x7006 (secondary)
      0xA000 (ECG wrapper)
      0xFFF0 (scales)
      6E800001-B5A3-F393-E0A9-E50E24DCCA9E (Nordic-style ECG)
  - Per-product device name prefixes (BM/BC/BF/AS/GL/PO/...).

Scale mfr-data carries the device MAC after a 0xFF sentinel byte
(captured at offsets sentinel+5..sentinel+10, byte-reversed before use).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


BEURER_COMPANY_ID = 0x043A

# Custom 128-bit UUIDs.
BEURER_CUSTOM_128_UUID = "d0a2ff00-2996-d38b-e214-86515df5a1df"
BEURER_NORDIC_ECG_UUID = "6e800001-b5a3-f393-e0a9-e50e24dcca9e"

# 16-bit "vendor on SIG base" UUIDs (Beurer-custom, NOT SIG profiles).
BEURER_BP_OXIMETER_UUID = "6006"
BEURER_SECONDARY_UUID = "7006"
BEURER_ECG_WRAPPER_UUID = "a000"
BEURER_SCALE_UUID = "fff0"

ALL_BEURER_UUIDS = (
    BEURER_CUSTOM_128_UUID,
    BEURER_NORDIC_ECG_UUID,
    BEURER_BP_OXIMETER_UUID,
    BEURER_SECONDARY_UUID,
    BEURER_ECG_WRAPPER_UUID,
    BEURER_SCALE_UUID,
)

# Product family classification by name prefix.
NAME_FAMILY_RULES = [
    (re.compile(r"^BM\d", re.IGNORECASE), "blood_pressure_monitor"),
    (re.compile(r"^BC\d", re.IGNORECASE), "body_composition_scale"),
    (re.compile(r"^BF\d", re.IGNORECASE), "bathroom_scale"),
    (re.compile(r"^AS\d", re.IGNORECASE), "activity_tracker"),
    (re.compile(r"^GL\d", re.IGNORECASE), "blood_glucose_monitor"),
    (re.compile(r"^PO\d", re.IGNORECASE), "pulse_oximeter"),
    (re.compile(r"^DELUXE|^PREMIUM|^SERIES|^ELITE|^SENSE", re.IGNORECASE), "rebrand_flagship"),
    (re.compile(r"^Beurer", re.IGNORECASE), "beurer_branded"),
]

# Family → service UUID family hint (the canonical primary UUID per family).
FAMILY_UUID_HINT = {
    "blood_pressure_monitor": BEURER_BP_OXIMETER_UUID,
    "body_composition_scale": BEURER_SCALE_UUID,
    "bathroom_scale": BEURER_SCALE_UUID,
    "activity_tracker": BEURER_CUSTOM_128_UUID,
    "blood_glucose_monitor": BEURER_BP_OXIMETER_UUID,
    "pulse_oximeter": BEURER_BP_OXIMETER_UUID,
}

_NAME_RE = re.compile(r"^(BM|BC|BF|AS|GL|PO|DELUXE|PREMIUM|SERIES|ELITE|SENSE|Beurer)", re.IGNORECASE)


def _extract_mac_from_scale_mfr(payload: bytes) -> str | None:
    """Extract the 6-byte MAC from a scale's mfr-data payload.

    Algorithm per `hj/a.java`: walk the payload; once a 0xFF sentinel is seen,
    skip 4 bytes, then the next 6 bytes are the MAC (little-endian — reverse
    before display).
    """
    if not payload:
        return None
    seen_sentinel = False
    captured: list[int] = []
    for b in payload:
        if not seen_sentinel:
            if b == 0xFF:
                seen_sentinel = True
            continue
        captured.append(b)
        if len(captured) >= 10:
            break
    if len(captured) < 10:
        return None
    mac_bytes = bytes(captured[4:10])
    reversed_mac = mac_bytes[::-1]
    return ":".join(f"{x:02X}" for x in reversed_mac)


@register_parser(
    name="beurer",
    company_id=BEURER_COMPANY_ID,
    service_uuid=ALL_BEURER_UUIDS,
    local_name_pattern=r"(?i)^(BM|BC|BF|AS|GL|PO|DELUXE|PREMIUM|SERIES|ELITE|SENSE|Beurer)",
    description="Beurer HealthManager (BP / scales / glucose / oximeter / ECG)",
    version="1.0.0",
    core=False,
)
class BeurerParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        cid_hit = raw.company_id == BEURER_COMPANY_ID
        uuid_hit = any(u in normalized or any(n.endswith(u) for n in normalized)
                       for u in ALL_BEURER_UUIDS)
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (cid_hit or uuid_hit or name_match):
            return None

        metadata: dict = {}

        # Family classification from name.
        if name_match and raw.local_name:
            for pattern, family in NAME_FAMILY_RULES:
                if pattern.match(raw.local_name):
                    metadata["product_family"] = family
                    break
            metadata["model_code"] = raw.local_name

        # Matched UUID family.
        for u in ALL_BEURER_UUIDS:
            if u in normalized or any(n.endswith(u) for n in normalized):
                metadata["matched_service_uuid"] = u
                break

        # Scale mfr-data carries the device MAC.
        if cid_hit:
            mac = _extract_mac_from_scale_mfr(raw.manufacturer_payload or b"")
            if mac:
                metadata["device_mac_in_mfr"] = mac

        identity_basis = (
            metadata.get("device_mac_in_mfr")
            or raw.local_name
            or raw.mac_address
        )
        id_hash = hashlib.sha256(f"beurer:{identity_basis}".encode()).hexdigest()[:16]
        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="beurer",
            beacon_type="beurer",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
