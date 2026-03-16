"""SmartDry laundry sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SMARTDRY_COMPANY_ID = 0x01AE


@register_parser(
    name="smartdry",
    company_id=SMARTDRY_COMPANY_ID,
    description="SmartDry laundry sensor",
    version="1.0.0",
    core=False,
)
class SmartDryParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 8:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != SMARTDRY_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 6:
            return None

        temp_raw = struct.unpack_from("<h", payload, 0)[0]
        humidity_raw = struct.unpack_from("<H", payload, 2)[0]
        battery = payload[4]
        shake = payload[5]

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:smartdry".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="smartdry",
            beacon_type="smartdry",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "temperature": temp_raw / 100.0,
                "humidity": humidity_raw / 100.0,
                "battery": battery,
                "shake_intensity": shake,
            },
        )

    def storage_schema(self):
        return None
