"""MEATER wireless meat thermometer plugin (detection only)."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

MEATER_COMPANY_ID = 0x037B


@register_parser(
    name="meater",
    company_id=MEATER_COMPANY_ID,
    local_name_pattern=r"^MEATER",
    description="MEATER wireless meat thermometer",
    version="1.0.0",
    core=False,
)
class MEATERParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        raw_hex = payload.hex() if payload else ""

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:MEATER".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="meater",
            beacon_type="meater",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata={},
        )

    def storage_schema(self):
        return None
