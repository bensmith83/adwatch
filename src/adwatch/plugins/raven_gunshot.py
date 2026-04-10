"""Raven gunshot detector (SoundThinking/ShotSpotter) BLE advertisement parser.

Detects SoundThinking Raven acoustic gunshot detection sensors by matching
the SoundThinking IEEE-registered OUI prefix (D4:11:D6). When service UUIDs
are advertised, estimates firmware version and maps available telemetry.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SOUNDTHINKING_OUI = "D4:11:D6"

# Raven GATT service UUIDs (full 128-bit Bluetooth base UUID form)
RAVEN_SERVICE_UUIDS = {
    "0000180a-0000-1000-8000-00805f9b34fb": "device_info",
    "00003100-0000-1000-8000-00805f9b34fb": "gps",
    "00003200-0000-1000-8000-00805f9b34fb": "power",
    "00003300-0000-1000-8000-00805f9b34fb": "network",
    "00003400-0000-1000-8000-00805f9b34fb": "uploads",
    "00003500-0000-1000-8000-00805f9b34fb": "diagnostics",
}

RAVEN_LEGACY_UUIDS = {
    "00001809-0000-1000-8000-00805f9b34fb": "health_legacy",
    "00001819-0000-1000-8000-00805f9b34fb": "location_legacy",
}

_ALL_UUIDS = {**RAVEN_SERVICE_UUIDS, **RAVEN_LEGACY_UUIDS}

_GPS_UUID = "00003100-0000-1000-8000-00805f9b34fb"
_POWER_UUID = "00003200-0000-1000-8000-00805f9b34fb"
_LEGACY_LOCATION_UUID = "00001819-0000-1000-8000-00805f9b34fb"


def _detect_services(service_uuids: list[str]) -> list[str]:
    services = []
    for uuid in service_uuids:
        name = _ALL_UUIDS.get(uuid.lower())
        if name:
            services.append(name)
    return services


def _estimate_firmware(service_uuids: list[str]) -> str:
    uuids_lower = {u.lower() for u in service_uuids}
    has_legacy_location = _LEGACY_LOCATION_UUID in uuids_lower
    has_gps = _GPS_UUID in uuids_lower
    has_power = _POWER_UUID in uuids_lower

    if has_legacy_location and not has_gps:
        return "1.1.x"
    if has_gps and not has_power:
        return "1.2.x"
    if has_gps and has_power:
        return "1.3.x"
    return "unknown"


# Non-standard service UUIDs unique to Raven (secondary detection if MAC is randomized)
RAVEN_DISTINCTIVE_UUIDS = [
    "00003100-0000-1000-8000-00805f9b34fb",  # GPS
    "00003200-0000-1000-8000-00805f9b34fb",  # Power
    "00003300-0000-1000-8000-00805f9b34fb",  # Network
    "00003400-0000-1000-8000-00805f9b34fb",  # Uploads
    "00003500-0000-1000-8000-00805f9b34fb",  # Diagnostics
]


@register_parser(
    name="raven_gunshot",
    mac_prefix=SOUNDTHINKING_OUI,
    service_uuid=RAVEN_DISTINCTIVE_UUIDS,
    description="SoundThinking Raven gunshot detector",
    version="1.0.0",
    core=False,
)
class RavenGunShotParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        services = _detect_services(raw.service_uuids or [])
        firmware = _estimate_firmware(raw.service_uuids or [])

        id_hash = hashlib.sha256(
            f"raven:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata = {
            "services": services,
            "firmware_estimate": firmware,
        }

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="raven_gunshot",
            beacon_type="raven_gunshot",
            device_class="surveillance",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else None,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
