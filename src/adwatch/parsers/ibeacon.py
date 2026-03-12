"""iBeacon parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="ibeacon",
    company_id=0x004C,
    description="Apple iBeacon",
    version="1.0",
    core=True,
)
class IBeaconParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 25:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            company_id_be = int.from_bytes(data[:2], "big")
            if company_id_be != 0x004C:
                return None

        subtype = data[2]
        length = data[3]
        if subtype != 0x02 or length != 0x15:
            return None

        uuid_bytes = data[4:20]
        uuid = (
            f"{uuid_bytes[0:4].hex()}-{uuid_bytes[4:6].hex()}-"
            f"{uuid_bytes[6:8].hex()}-{uuid_bytes[8:10].hex()}-"
            f"{uuid_bytes[10:16].hex()}"
        )
        major = struct.unpack(">H", data[20:22])[0]
        minor = struct.unpack(">H", data[22:24])[0]
        tx_power = struct.unpack("b", data[24:25])[0]

        identifier_hash = hashlib.sha256(
            f"{uuid}:{major}:{minor}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ibeacon",
            beacon_type="ibeacon",
            device_class="beacon",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "uuid": uuid,
                "major": major,
                "minor": minor,
                "tx_power": tx_power,
            },
        )
