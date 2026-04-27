"""Owlet Baby Care BLE advertisement parser.

Owlet Smart Sock / Dream Sock baby HR + SpO2 monitor. Triple-signal match:
SIG company ID 0x0E9F, service UUID c5163c4b-9b63-570d-a3a8-407716f04276,
local name "OB". Name alone is too short to be safe — require UUID or CID.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


OWLET_COMPANY_ID = 0x0E9F
OWLET_SERVICE_UUID = "c5163c4b-9b63-570d-a3a8-407716f04276"
_OWLET_UUID_NORMALIZED = _normalize_uuid(OWLET_SERVICE_UUID)


@register_parser(
    name="owlet",
    company_id=OWLET_COMPANY_ID,
    service_uuid=OWLET_SERVICE_UUID,
    description="Owlet baby HR/SpO2 monitor (Smart Sock / Dream Sock)",
    version="1.0.0",
    core=False,
)
class OwletParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == OWLET_COMPANY_ID
        )
        has_uuid = any(
            _normalize_uuid(u) == _OWLET_UUID_NORMALIZED
            for u in (raw.service_uuids or [])
        )

        if not (has_company or has_uuid):
            return None

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if has_uuid:
            metadata["has_owlet_service"] = True
        if has_company:
            metadata["company_id_hex"] = f"0x{OWLET_COMPANY_ID:04X}"

        id_hash = hashlib.sha256(f"owlet:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="owlet",
            beacon_type="owlet",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )
