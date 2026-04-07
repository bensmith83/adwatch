"""TC100 thermocouple/thermometer BLE advertisement parser.

TC100 devices advertise with custom service UUID 8801 and company ID 0x1987.
The local name follows the pattern TC100_XXXX where XXXX is a hex device ID
that also appears in the manufacturer data payload.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

TC100_COMPANY_ID = 0x1987
TC100_SERVICE_UUID = "8801"
NAME_RE = re.compile(r"^TC100_([0-9A-Fa-f]{4})")


@register_parser(
    name="tc100",
    company_id=TC100_COMPANY_ID,
    service_uuid=TC100_SERVICE_UUID,
    local_name_pattern=r"^TC100_",
    description="TC100 thermocouple/thermometer advertisements",
    version="1.0.0",
    core=False,
)
class TC100Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = TC100_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)
        company_match = raw.company_id == TC100_COMPANY_ID

        if not uuid_match and not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(f"tc100:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["device_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        if raw.manufacturer_payload and len(raw.manufacturer_payload) >= 8:
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="tc100",
            beacon_type="tc100",
            device_class="thermometer",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
