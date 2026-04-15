"""Google FE9F BLE advertisement parser.

Undocumented Google BLE service (UUID 0xFE9F). Appears on Android devices
running Google services. Purpose unknown — possibly an older or internal
Nearby/presence service.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

GOOGLE_FE9F_UUID = "fe9f"


@register_parser(
    name="google_fe9f",
    service_uuid=GOOGLE_FE9F_UUID,
    description="Google FE9F BLE service",
    version="1.0.0",
    core=False,
)
class GoogleFe9fParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or GOOGLE_FE9F_UUID not in raw.service_data:
            return None

        data = raw.service_data[GOOGLE_FE9F_UUID]
        if not data:
            return None

        id_hash = hashlib.sha256(
            f"google_fe9f:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="google_fe9f",
            beacon_type="google_fe9f",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "payload_hex": data.hex(),
                "payload_length": len(data),
            },
        )
