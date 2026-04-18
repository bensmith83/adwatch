"""Milwaukee ONE-KEY tool BLE advertisement parser.

Per apk-ble-hunting/reports/milwaukeetool-mymilwaukee_passive.md. Primary SIG
service UUID 0xFDF5 + legacy 128-bit UUID. Manufacturer-data has two variants
(Light / OneKeyCardTool) — byte layout not recoverable from the APK Java.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MILWAUKEE_COMPANY_ID = 0x0604
MILWAUKEE_SERVICE_UUID_SIG = "fdf5"
MILWAUKEE_SERVICE_UUID_LEGACY = "a3e68a83-4c4d-4778-bd0a-829fb434a7a1"


@register_parser(
    name="milwaukee_onekey",
    company_id=MILWAUKEE_COMPANY_ID,
    service_uuid=[MILWAUKEE_SERVICE_UUID_SIG, MILWAUKEE_SERVICE_UUID_LEGACY],
    description="Milwaukee ONE-KEY tools and lights",
    version="1.0.0",
    core=False,
)
class MilwaukeeOneKeyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == MILWAUKEE_COMPANY_ID
        )
        has_uuid = any(
            u.lower() in (MILWAUKEE_SERVICE_UUID_SIG, MILWAUKEE_SERVICE_UUID_LEGACY)
            for u in (raw.service_uuids or [])
        )

        if not (has_company or has_uuid):
            return None

        metadata: dict = {}
        if has_uuid:
            metadata["has_onekey_service"] = True

        payload = raw.manufacturer_payload
        if has_company and payload:
            metadata["payload_hex"] = payload.hex()
            metadata["payload_length"] = len(payload)
            # Byte layout not recoverable from the companion app — exposing
            # the raw bytes for field observation.

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"milwaukee_onekey:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="milwaukee_onekey",
            beacon_type="milwaukee_onekey",
            device_class="power_tool",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
