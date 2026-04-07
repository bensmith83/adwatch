"""iHealth BLE smart health device advertisement parser.

iHealth Labs devices advertise with service UUID FE4A (Bluetooth SIG assigned)
and company ID 0x020E. Local names follow the pattern BLESmart_XXXX where XXXX
is a hex-encoded device identifier.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

IHEALTH_COMPANY_ID = 0x020E
IHEALTH_SERVICE_UUID = "fe4a"
NAME_RE = re.compile(r"^BLESmart_([0-9A-Fa-f]+)")


@register_parser(
    name="ihealth",
    company_id=IHEALTH_COMPANY_ID,
    service_uuid=IHEALTH_SERVICE_UUID,
    local_name_pattern=r"^BLESmart_",
    description="iHealth smart health device advertisements",
    version="1.0.0",
    core=False,
)
class IHealthParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = IHEALTH_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)
        company_match = raw.company_id == IHEALTH_COMPANY_ID

        if not uuid_match and not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(f"ihealth:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["device_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="ihealth",
            beacon_type="ihealth",
            device_class="health_monitor",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
