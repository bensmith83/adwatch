"""Amphiro smart shower head plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SERVICE_UUID = "7f402200-504f-4c41-5261-6d706869726f"


@register_parser(
    name="amphiro",
    service_uuid=SERVICE_UUID,
    description="Amphiro smart shower head (water usage, temperature, energy)",
    version="1.0.0",
    core=False,
)
class AmphiroParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        data = raw.service_data.get(SERVICE_UUID)
        if not data or len(data) < 12:
            return None

        session_id, volume_raw, temp_raw, duration, energy = struct.unpack_from(
            "<IHHHH", data, 0
        )

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:amphiro".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="amphiro",
            beacon_type="amphiro",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "session_id": session_id,
                "water_volume": volume_raw / 10.0,
                "water_temperature": temp_raw / 10.0,
                "duration": duration,
                "energy": energy,
            },
        )

    def storage_schema(self):
        return None
