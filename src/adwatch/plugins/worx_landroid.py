"""Worx Landroid (Positec) robotic mower BLE advertisement parser.

Per apk-ble-hunting/reports/positec-landroid_passive.md. Pure service-UUID
detection (0xABF0 vendor UUID under SIG base); all state behind GATT connect.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WORX_SERVICE_UUID = "abf0"


@register_parser(
    name="worx_landroid",
    service_uuid=WORX_SERVICE_UUID,
    description="Worx Landroid robotic mowers (Positec)",
    version="1.0.0",
    core=False,
)
class WorxLandroidParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if WORX_SERVICE_UUID not in [u.lower() for u in (raw.service_uuids or [])]:
            return None

        metadata: dict = {"has_worx_service": True}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"worx:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="worx_landroid",
            beacon_type="worx_landroid",
            device_class="mower",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
