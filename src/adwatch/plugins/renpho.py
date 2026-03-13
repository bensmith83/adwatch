"""Renpho/Etekcity smart scale plugin (detection only)."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

RENPHO_COMPANY_ID = 0x06D0


@register_parser(
    name="renpho",
    company_id=RENPHO_COMPANY_ID,
    local_name_pattern=r"^QN-Scale$",
    description="Renpho/Etekcity smart scales",
    version="1.0.0",
    core=False,
)
class RenphoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or "QN-Scale"

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{local_name}".encode()
        ).hexdigest()[:16]

        payload = raw.manufacturer_payload
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="renpho",
            beacon_type="renpho",
            device_class="scale",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata={},
        )

    def storage_schema(self):
        return None
