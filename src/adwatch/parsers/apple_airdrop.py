"""Apple AirDrop parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

AIRDROP_TYPE = 0x05


@register_parser(
    name="apple_airdrop",
    company_id=0x004C,
    description="Apple AirDrop",
    version="1.0",
    core=True,
)
class AppleAirDropParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        if tlv_type != AIRDROP_TYPE:
            return None

        tlv_len = data[3]
        tlv_value = data[4:]
        if len(tlv_value) < 8:
            return None

        appleid_hash = tlv_value[0:2].hex()
        phone_hash = tlv_value[2:4].hex()
        email_hash = tlv_value[4:6].hex()
        email2_hash = tlv_value[6:8].hex()

        combined = appleid_hash + phone_hash + email_hash + email2_hash
        identifier_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_airdrop",
            beacon_type="apple_airdrop",
            device_class="phone",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "appleid_hash": appleid_hash,
                "phone_hash": phone_hash,
                "email_hash": email_hash,
                "email2_hash": email2_hash,
            },
        )
