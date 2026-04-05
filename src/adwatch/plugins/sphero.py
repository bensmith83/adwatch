"""Sphero robot BLE advertisement parser.

Sphero BOLT (and other Sphero robots) advertise with the custom service
UUID 00010001-574F-4F20-5370-6865726F2121 ("WOO Sphero!!") and local
names matching the pattern SB-XXXX (4-char hex device ID).
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SPHERO_SERVICE_UUID = "00010001-574f-4f20-5370-6865726f2121"
SPHERO_NAME_RE = re.compile(r"^SB-([A-F0-9]{4})$")


@register_parser(
    name="sphero",
    service_uuid=SPHERO_SERVICE_UUID,
    local_name_pattern=r"^SB-[A-F0-9]{4}$",
    description="Sphero robot advertisements",
    version="1.0.0",
    core=False,
)
class SpherParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = SPHERO_SERVICE_UUID in raw.service_uuids
        name_match = raw.local_name is not None and SPHERO_NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"sphero:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {"model": "BOLT"}
        if name_match:
            metadata["device_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="sphero",
            beacon_type="sphero",
            device_class="toy",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
