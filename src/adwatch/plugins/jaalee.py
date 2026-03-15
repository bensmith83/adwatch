"""Jaalee BLE temperature/humidity sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="jaalee",
    service_uuid="9717",
    description="Jaalee temperature/humidity sensor",
    version="1.0.0",
    core=False,
)
class JaaleeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or "9717" not in raw.service_data:
            return None

        data = raw.service_data["9717"]
        if len(data) < 5:
            return None

        temp_raw, humidity_raw, battery = struct.unpack_from("<hHB", data, 0)

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:jaalee".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="jaalee",
            beacon_type="jaalee",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "temperature": temp_raw / 100.0,
                "humidity": humidity_raw / 100.0,
                "battery": battery,
            },
        )

    def storage_schema(self):
        return None
