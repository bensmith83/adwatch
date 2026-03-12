"""Apple AirPlay Target parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

AIRPLAY_TYPE = 0x09


@register_parser(
    name="apple_airplay",
    company_id=0x004C,
    description="Apple AirPlay Target",
    version="1.0",
    core=True,
)
class AppleAirPlayParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        if tlv_type != AIRPLAY_TYPE:
            return None

        tlv_len = data[3]
        tlv_value = data[4:]
        if len(tlv_value) < 3 or tlv_len < 3:
            return None

        flags = tlv_value[0]
        config_seed = struct.unpack(">H", tlv_value[1:3])[0]

        metadata = {
            "flags": flags,
            "config_seed": config_seed,
        }

        if tlv_len >= 10 and len(tlv_value) >= 10:
            ipv4_bytes = tlv_value[6:10]
            metadata["ipv4"] = ".".join(str(b) for b in ipv4_bytes)

        payload_hex = tlv_value[:tlv_len].hex()
        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{payload_hex}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_airplay",
            beacon_type="apple_airplay",
            device_class="media",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata=metadata,
        )
