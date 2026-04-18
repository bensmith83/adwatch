"""FLIR Tools BLE advertisement parser.

Per apk-ble-hunting/reports/flir-tools_passive.md. Company ID 0x0AE9 for
FLIR One thermal cameras; Meterlink meters use a separate service UUID.
Byte offsets inside mfr data are in native code — not decoded here.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


FLIR_COMPANY_ID = 0x0AE9
METERLINK_UUID = "d813bf66-5e61-188c-3d47-2487320a8b6e"


@register_parser(
    name="flir_tools",
    company_id=FLIR_COMPANY_ID,
    service_uuid=METERLINK_UUID,
    local_name_pattern=r"(?i)^FLIR",
    description="FLIR thermal cameras and Meterlink meters",
    version="1.0.0",
    core=False,
)
class FlirToolsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == FLIR_COMPANY_ID
        )
        has_uuid = METERLINK_UUID in [u.lower() for u in (raw.service_uuids or [])]
        name = raw.local_name or ""
        name_match = name.lower().startswith("flir")

        if not (has_company or has_uuid or name_match):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if has_company:
            metadata["product_family"] = "FLIR One thermal"
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()
        elif has_uuid:
            metadata["product_family"] = "Meterlink"

        id_hash = hashlib.sha256(f"flir:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="flir_tools",
            beacon_type="flir_tools",
            device_class="imaging_tool",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )
