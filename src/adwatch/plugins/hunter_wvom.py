"""Hunter Industries WVOM (Wireless Valve Output Module) BLE advertisement parser.

WVOM modules for Hunter ICC2/HCC irrigation controllers advertise with a
custom 128-bit service UUID and local names like "WVOM-147516".
The advertisement is a discovery beacon — no sensor data in the ads.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

WVOM_SERVICE_UUID = "0ed3e3d3-8cd8-4f29-8fec-a7d3a2c5443e"
WVOM_NAME_RE = re.compile(r"^WVOM-(\d+)")


@register_parser(
    name="hunter_wvom",
    service_uuid=WVOM_SERVICE_UUID,
    local_name_pattern=r"^WVOM-",
    description="Hunter Industries WVOM irrigation controller advertisements",
    version="1.0.0",
    core=False,
)
class HunterWvomParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = any(WVOM_SERVICE_UUID in u for u in raw.service_uuids)
        name_match = raw.local_name and WVOM_NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:hunter_wvom".encode()
        ).hexdigest()[:16]

        metadata: dict = {}

        if name_match:
            metadata["serial_number"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="hunter_wvom",
            beacon_type="hunter_wvom",
            device_class="irrigation",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
