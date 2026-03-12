"""BlueMaestro Tempo Disc environmental sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

BLUEMAESTRO_COMPANY_ID = 0x0133


@register_parser(
    name="bluemaestro",
    company_id=BLUEMAESTRO_COMPANY_ID,
    local_name_pattern=r"^T[A-Z]?\d",
    description="BlueMaestro Tempo Disc environmental sensors",
    version="1.0.0",
    core=False,
)
class BlueMaestroParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 20:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != BLUEMAESTRO_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 18:
            return None

        version = payload[0]
        battery = payload[1]
        temp = struct.unpack_from(">h", payload, 2)[0]
        humidity = struct.unpack_from(">H", payload, 4)[0]
        dewpoint = struct.unpack_from(">h", payload, 6)[0]
        max_temp = struct.unpack_from(">h", payload, 8)[0]
        min_temp = struct.unpack_from(">h", payload, 10)[0]
        max_hum = struct.unpack_from(">H", payload, 12)[0]
        min_hum = struct.unpack_from(">H", payload, 14)[0]
        interval = struct.unpack_from(">H", payload, 16)[0]

        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="bluemaestro",
            beacon_type="bluemaestro",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "temperature_c": temp / 10.0,
                "humidity": humidity / 10.0,
                "dewpoint_c": dewpoint / 10.0,
                "battery": battery,
                "max_temp_c": max_temp / 10.0,
                "min_temp_c": min_temp / 10.0,
                "max_humidity": max_hum / 10.0,
                "min_humidity": min_hum / 10.0,
                "interval_s": interval,
            },
        )

    def storage_schema(self):
        return None
