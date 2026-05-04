"""Garmin wearable BLE advertisement plugin.

Identifiers per apk-ble-hunting/reports/garmin-apps-connectmobile_passive.md.
Manufacturer-data byte layout is NOT documented in the Connect app (no
`getManufacturerSpecificData()` calls) — the `message_type` field below is
best-effort from historical captures, not authoritative.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


GARMIN_COMPANY_ID = 0x0087
GARMIN_SERVICE_UUID_MODERN = "fe1f"
GARMIN_SERVICE_UUID_LEGACY = "00001001-7791-11e2-9452-f23c91aec05e"
# GFDI control service — exposed once a watch is paired to Connect; per
# apk-ble-hunting/reports/garmin-connect_passive.md.
GARMIN_SERVICE_UUID_GFDI = "6a4e4350-667b-11e3-949a-0800200c9a66"

# Known Garmin product families per passive report (scanner implementation
# notes). Case-sensitive prefix match.
GARMIN_NAME_PREFIXES = (
    "Forerunner", "fenix", "Fenix", "Edge", "vivo", "Vivo", "venu", "Venu",
    "Instinct", "Approach", "Descent", "epix", "Epix", "Tactix", "Enduro",
    "Lily", "Marq", "MARQ", "Quatix", "Swim", "Varia", "Vector", "Rally",
    "InReach", "HRM-", "HRM ", "Index",
)

_GARMIN_NAME_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in GARMIN_NAME_PREFIXES) + r")"
)


def _device_class_from_name(local_name: str) -> str:
    if local_name.startswith("HRM-") or local_name.startswith("HRM "):
        return "heart_rate_monitor"
    if local_name.startswith("Edge"):
        return "cycling_computer"
    if local_name.startswith("Index"):
        return "scale"
    if local_name.startswith(("Varia",)):
        return "cycling_sensor"
    if local_name.startswith(("Vector", "Rally")):
        return "power_meter"
    if local_name.startswith("InReach"):
        return "satellite_messenger"
    return "wearable"


@register_parser(
    name="garmin",
    company_id=GARMIN_COMPANY_ID,
    service_uuid=[GARMIN_SERVICE_UUID_MODERN, GARMIN_SERVICE_UUID_LEGACY, GARMIN_SERVICE_UUID_GFDI],
    local_name_pattern=_GARMIN_NAME_RE.pattern,
    description="Garmin wearable advertisements",
    version="1.2.0",
    core=False,
)
class GarminParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""

        has_mfr = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 3
            and int.from_bytes(raw.manufacturer_data[:2], "little") == GARMIN_COMPANY_ID
        )
        has_uuid = any(
            u.lower() in (
                GARMIN_SERVICE_UUID_MODERN,
                GARMIN_SERVICE_UUID_LEGACY,
                GARMIN_SERVICE_UUID_GFDI,
            )
            for u in (raw.service_uuids or [])
        )
        name_match = bool(local_name and _GARMIN_NAME_RE.match(local_name))

        if not (has_mfr or has_uuid or name_match):
            return None

        metadata: dict = {}
        payload_hex = ""
        if has_mfr:
            payload = raw.manufacturer_data[2:]
            payload_hex = payload.hex()
            metadata["message_type"] = payload[0]
        if has_uuid:
            metadata["has_garmin_service_uuid"] = True

        device_class = _device_class_from_name(local_name) if local_name else "wearable"

        if local_name:
            first_word = re.split(r"[\s\-]", local_name)[0]
            device_family = first_word[0].upper() + first_word[1:] if first_word else "Unknown"
        else:
            device_family = "Unknown"
        metadata["device_family"] = device_family
        metadata["model"] = local_name if local_name else "Unknown"

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:garmin".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="garmin",
            beacon_type="garmin",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=payload_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
