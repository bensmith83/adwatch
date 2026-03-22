"""LG TV BLE advertisement parser.

Parses manufacturer data from LG webOS TVs.
Company ID 0x00C4, service UUID feb9.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

LG_COMPANY_ID = 0x00C4


@register_parser(
    name="lg_tv",
    company_id=LG_COMPANY_ID,
    service_uuid="feb9",
    description="LG webOS TV advertisements",
    version="1.0.0",
    core=False,
)
class LGTVParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 3:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != LG_COMPANY_ID:
            return None

        flags = data[2]

        # Extract model from local_name
        model = None
        prefix = "[LG] webOS TV "
        if raw.local_name and raw.local_name.startswith(prefix):
            model = raw.local_name[len(prefix):]

        id_hash = hashlib.sha256(
            f"lg_tv:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata = {"flags": flags}
        if model:
            metadata["model"] = model

        return ParseResult(
            parser_name="lg_tv",
            beacon_type="lg_tv",
            device_class="tv",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
