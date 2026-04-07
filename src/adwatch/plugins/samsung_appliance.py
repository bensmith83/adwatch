"""Samsung appliance BLE advertisement parser.

Samsung smart appliances (refrigerators, washers, etc.) advertise with
company ID 0x0075 (Samsung Electronics). These are distinct from Samsung
TV and Galaxy Buds advertisements which have their own parsers.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SAMSUNG_COMPANY_ID = 0x0075


@register_parser(
    name="samsung_appliance",
    company_id=SAMSUNG_COMPANY_ID,
    description="Samsung smart appliance advertisements",
    version="1.0.0",
    core=False,
)
class SamsungApplianceParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != SAMSUNG_COMPANY_ID:
            return None

        id_hash = hashlib.sha256(f"samsung_appliance:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if raw.manufacturer_payload:
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="samsung_appliance",
            beacon_type="samsung_appliance",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
