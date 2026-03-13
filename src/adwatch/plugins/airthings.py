"""Airthings Wave air quality monitor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

AIRTHINGS_COMPANY_ID = 0x0334

MODEL_PREFIXES = {
    "2900": "Wave Gen 1",
    "2920": "Wave Mini",
    "2930": "Wave Plus",
    "2950": "Wave Radon Gen 2",
    "3210": "Wave Enhance EU",
    "3220": "Wave Enhance US",
    "3250": "Corentium Home 2",
}


@register_parser(
    name="airthings",
    company_id=AIRTHINGS_COMPANY_ID,
    description="Airthings Wave air quality monitors",
    version="1.0.0",
    core=False,
)
class AirthingsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        if not payload or len(payload) < 4:
            return None

        serial_number = struct.unpack_from("<I", payload, 0)[0]
        serial_str = str(serial_number)
        prefix = serial_str[:4] if len(serial_str) >= 4 else ""
        model = MODEL_PREFIXES.get(prefix, "Unknown")

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{serial_number}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="airthings",
            beacon_type="airthings",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "serial_number": serial_number,
                "model": model,
            },
        )

    def storage_schema(self):
        return None
