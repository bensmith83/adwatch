"""iBBQ / Inkbird BBQ thermometer plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="ibbq",
    company_id=0x0000,
    local_name_pattern=r"^iBBQ$",
    description="iBBQ / Inkbird BBQ thermometer",
    version="1.0.0",
    core=False,
)
class IBBQParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 14:
            return None

        payload = raw.manufacturer_data
        # Format: company_id(2) + reserved(4) + mac(6) + temps(2*N)
        # Temps start at offset 12
        temp_data = payload[12:]
        if len(temp_data) < 2:
            return None

        probe_count = len(temp_data) // 2
        metadata: dict = {"probe_count": probe_count}

        for i in range(probe_count):
            raw_temp = struct.unpack_from("<h", temp_data, i * 2)[0]
            # Sentinel value for disconnected probe (0xFFF6 = -10 signed)
            if raw_temp == -10:
                continue
            metadata[f"probe_{i + 1}_temp_c"] = raw_temp / 10.0

        id_hash = hashlib.sha256(f"{raw.mac_address}:iBBQ".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ibbq",
            beacon_type="ibbq",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
