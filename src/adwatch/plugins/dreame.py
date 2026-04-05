"""Dreame robot vacuum BLE advertisement parser.

Dreame robot vacuums advertise with service UUID FD92 and local names
matching DL-XXXXXXXXXX (serial number).
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

DREAME_SERVICE_UUID = "FD92"
DREAME_SERVICE_UUID_FULL = "0000fd92-0000-1000-8000-00805f9b34fb"
DREAME_NAME_RE = re.compile(r"^DL-(\S+)")


@register_parser(
    name="dreame",
    service_uuid=DREAME_SERVICE_UUID,
    local_name_pattern=r"^DL-",
    description="Dreame robot vacuum advertisements",
    version="1.0.0",
    core=False,
)
class DreameParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = DREAME_SERVICE_UUID_FULL in raw.service_uuids
        name_match = raw.local_name is not None and DREAME_NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"dreame:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["serial"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="dreame",
            beacon_type="dreame",
            device_class="vacuum",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
