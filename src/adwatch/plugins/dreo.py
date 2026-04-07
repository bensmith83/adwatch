"""DREO fan/appliance BLE advertisement parser.

DREO smart fans and air circulators advertise with custom service UUID 5348
and company ID 0x4648 ("HF"). The local name follows the pattern DREO{model_id}
where the suffix encodes the product model.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

DREO_COMPANY_ID = 0x4648
DREO_SERVICE_UUID = "5348"
NAME_RE = re.compile(r"^DREO(.+)")


@register_parser(
    name="dreo",
    company_id=DREO_COMPANY_ID,
    service_uuid=DREO_SERVICE_UUID,
    local_name_pattern=r"^DREO",
    description="DREO fan/appliance advertisements",
    version="1.0.0",
    core=False,
)
class DreoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = DREO_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)
        company_match = raw.company_id == DREO_COMPANY_ID

        if not uuid_match and not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(f"dreo:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["model_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="dreo",
            beacon_type="dreo",
            device_class="fan",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
