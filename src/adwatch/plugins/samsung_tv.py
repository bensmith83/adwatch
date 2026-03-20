"""Samsung TV BLE advertisement parser.

Parses manufacturer data from Samsung TVs and soundbars.
Company ID 0x0075. Type bytes at offset 2-3 (after company_id).
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SAMSUNG_COMPANY_ID = 0x0075


@register_parser(
    name="samsung_tv",
    company_id=SAMSUNG_COMPANY_ID,
    description="Samsung TV and soundbar advertisements",
    version="1.0.0",
    core=False,
)
class SamsungTVParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != SAMSUNG_COMPANY_ID:
            return None

        type_bytes = data[2:4].hex()

        # Extract model and device class from local_name
        model = None
        device_class = "tv"
        name = raw.local_name
        if name:
            if name.startswith("[TV] "):
                model = name[5:]
                device_class = "tv"
            elif name.startswith("[AV] "):
                model = name[5:]
                device_class = "soundbar"
            elif "Crystal UHD" in name:
                device_class = "tv"

        id_hash = hashlib.sha256(
            f"samsung_tv:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata = {"type_bytes": type_bytes}
        if model:
            metadata["model"] = model

        return ParseResult(
            parser_name="samsung_tv",
            beacon_type="samsung_tv",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
