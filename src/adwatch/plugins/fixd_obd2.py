"""FIXD Automotive OBD-II BLE scanner plugin.

FIXD is a Bluetooth OBD-II diagnostic dongle that plugs into a car's
diagnostic port. It reads check engine codes (DTCs) and vehicle health
data, relaying them to a phone app over BLE.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

FIXD_SERVICE_UUID = "fff0"
FIXD_NAME = "FIXD"


@register_parser(
    name="fixd_obd2",
    local_name_pattern=r"^FIXD$",
    description="FIXD automotive OBD-II scanner",
    version="1.0.0",
    core=False,
)
class FixdObd2Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # FIXD always advertises with local name "FIXD"
        # FFF0 is too generic to match on alone — require name
        if raw.local_name != FIXD_NAME:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {"device_name": FIXD_NAME}

        has_fff0 = any(
            "fff0" in u.lower() for u in (raw.service_uuids or [])
        )
        if has_fff0:
            metadata["has_obd_service"] = True

        return ParseResult(
            parser_name="fixd_obd2",
            beacon_type="fixd_obd2",
            device_class="automotive",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
