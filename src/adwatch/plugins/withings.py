"""Withings health-device BLE advertisement parser.

Scales, blood-pressure monitors, watches, sleep monitors, thermometers — all
use SIG base UUIDs in the 0x9990-0x9999 range plus a `-5749-5448-` "WITH"
marker on the custom-base UUIDs. Per
apk-ble-hunting/reports/withings-wiscale2_passive.md.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


# 16-bit SIG UUIDs → product model per passive report.
UUID_TO_MODEL = {
    "9990": "WBS06 (Body+/Cardio scale)",
    "9993": "WBS04 (scale)",
    "9994": "WBS05 (scale)",
    "9998": "WBS02 (Smart Body Analyser) / WSD01",
    "9999": "WPM02/03 (BPM) / WBS03 / WAM01",
}

_WITHINGS_SIG_UUIDS = tuple(UUID_TO_MODEL.keys())

# Custom-base pattern: bytes 4-7 = ASCII "WITH" (49 54 48 57 in LE → 5749 5448).
_WITH_MARKER_RE = re.compile(
    r"^[0-9a-f]{8}-5749-5448-[0-9a-f]{4}-[0-9a-f]{12}$"
)

# Known device-name prefixes.
WITHINGS_NAME_RE = re.compile(r"^(?:bl_hwa|WSM02|WBS0[23456]|WPM0[34]|WAM01|WSD01)")

UNPROVISIONED_MAC = "FF:FF:FF:FF:FF:FF"
PROVISIONING_MAC = "03:FF:FF:FF:FF:FF"


def _matches_with_marker(uuid: str) -> bool:
    return bool(_WITH_MARKER_RE.match(uuid.lower()))


@register_parser(
    name="withings",
    service_uuid=list(_WITHINGS_SIG_UUIDS),
    local_name_pattern=WITHINGS_NAME_RE.pattern,
    description="Withings scales, BPMs, watches, sleep monitors, thermometers",
    version="1.0.0",
    core=False,
)
class WithingsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}
        matched = False
        model = None

        # Service UUID identification.
        for u in (raw.service_uuids or []):
            n = _normalize_uuid(u)
            short = n[4:8] if len(n) >= 8 else ""
            if short in UUID_TO_MODEL:
                matched = True
                model = UUID_TO_MODEL[short]
                metadata["sig_uuid"] = short
                break
            if _matches_with_marker(n):
                matched = True
                metadata["with_marker_uuid"] = n
                break

        # Name identification.
        if raw.local_name and WITHINGS_NAME_RE.match(raw.local_name):
            matched = True

        # Manufacturer data: 6-byte device MAC after company ID.
        device_mac_from_mfr = None
        provisioning_state = None
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 8:
            payload = raw.manufacturer_data[2:]
            if len(payload) >= 6:
                mac_bytes = payload[:6]
                device_mac_from_mfr = ":".join(f"{b:02X}" for b in mac_bytes)
                if device_mac_from_mfr == UNPROVISIONED_MAC:
                    provisioning_state = "unprovisioned"
                elif device_mac_from_mfr == PROVISIONING_MAC:
                    provisioning_state = "provisioning"
                else:
                    provisioning_state = "paired"

        if not matched:
            return None

        if model:
            metadata["model"] = model
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if device_mac_from_mfr:
            metadata["mfr_data_mac"] = device_mac_from_mfr
            metadata["provisioning_state"] = provisioning_state

        if device_mac_from_mfr and provisioning_state == "paired":
            id_basis = f"withings:{device_mac_from_mfr}"
        else:
            id_basis = f"withings:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data[2:].hex() if raw.manufacturer_data and len(raw.manufacturer_data) > 2 else ""

        return ParseResult(
            parser_name="withings",
            beacon_type="withings",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
