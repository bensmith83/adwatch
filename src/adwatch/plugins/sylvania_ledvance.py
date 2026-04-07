"""Sylvania/LEDVANCE smart light BLE advertisement parser.

Sylvania (SIL:) and LEDVANCE (DUE:) smart lights advertise with service
UUID FDC1 and company ID 0x0819. The local name encodes brand prefix and
a 4-character hex device identifier.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SYLVANIA_COMPANY_ID = 0x0819
SYLVANIA_SERVICE_UUID = "fdc1"
NAME_RE = re.compile(r"^(SIL|DUE):([0-9A-Fa-f]{4})$")

BRAND_MAP = {
    "SIL": "Sylvania",
    "DUE": "LEDVANCE",
}


@register_parser(
    name="sylvania_ledvance",
    company_id=SYLVANIA_COMPANY_ID,
    service_uuid=SYLVANIA_SERVICE_UUID,
    local_name_pattern=r"^(SIL|DUE):",
    description="Sylvania/LEDVANCE smart light advertisements",
    version="1.0.0",
    core=False,
)
class SylvaniaLedvanceParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = SYLVANIA_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)
        company_match = raw.company_id == SYLVANIA_COMPANY_ID

        if not uuid_match and not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(f"sylvania_ledvance:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["brand"] = BRAND_MAP.get(name_match.group(1), name_match.group(1))
            metadata["device_id"] = name_match.group(2)
            metadata["device_name"] = raw.local_name

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="sylvania_ledvance",
            beacon_type="sylvania_ledvance",
            device_class="smart_light",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
