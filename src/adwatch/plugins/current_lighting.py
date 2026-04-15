"""HLI Solutions / GE Current Lighting sensor BLE advertisement parser.

Commercial smart building occupancy/lighting sensors from HLI Solutions
(formerly GE Current). These sensors broadcast zone info and room names
via BLE for building management systems.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

HLI_COMPANY_ID = 0x06DF

# Minimum payload: 2 (company ID) + 15 (data) = 17 bytes
MIN_DATA_LENGTH = 17


@register_parser(
    name="current_lighting",
    company_id=HLI_COMPANY_ID,
    description="HLI Solutions / GE Current lighting sensors",
    version="1.0.0",
    core=False,
)
class CurrentLightingParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < MIN_DATA_LENGTH:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != HLI_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        device_type = payload[1]  # byte 3 overall
        zone_id = payload[11]  # byte 13 overall

        id_hash = hashlib.sha256(
            f"current_lighting:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "device_type": device_type,
            "zone_id": zone_id,
            "payload_length": len(payload),
            "payload_hex": payload.hex(),
        }

        if raw.local_name:
            metadata["room_name"] = raw.local_name

        return ParseResult(
            parser_name="current_lighting",
            beacon_type="current_lighting",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
