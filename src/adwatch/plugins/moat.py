"""Moat temperature/humidity sensor plugin."""

import hashlib
import re
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

MOAT_NAME_RE = re.compile(r"^Moat_S")


@register_parser(
    name="moat",
    local_name_pattern=r"^Moat_S",
    description="Moat temperature/humidity sensors",
    version="1.0.0",
    core=False,
)
class MoatParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name or not MOAT_NAME_RE.match(raw.local_name):
            return None

        if not raw.manufacturer_data or len(raw.manufacturer_data) < 6:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 4:
            return None

        temp_raw = struct.unpack_from("<h", payload, 0)[0]
        humidity_raw = struct.unpack_from("<H", payload, 2)[0]

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{raw.local_name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="moat",
            beacon_type="moat",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "temperature_c": temp_raw / 100.0,
                "humidity": humidity_raw / 100.0,
            },
        )

    def storage_schema(self):
        return None
