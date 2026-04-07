"""Samsung SmartThings BLE advertisement parser.

SmartThings devices advertise with service UUID 1122 and local names
following the pattern S{16_hex_chars}C. The hex string in the name
serves as a device identifier.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SMARTTHINGS_SERVICE_UUID = "1122"
NAME_RE = re.compile(r"^S([0-9a-f]{16})C$", re.I)


@register_parser(
    name="smartthings",
    service_uuid=SMARTTHINGS_SERVICE_UUID,
    local_name_pattern=r"^S[0-9a-fA-F]{16}C$",
    description="Samsung SmartThings device advertisements",
    version="1.0.0",
    core=False,
)
class SmartThingsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = SMARTTHINGS_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"smartthings:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["device_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="smartthings",
            beacon_type="smartthings",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
