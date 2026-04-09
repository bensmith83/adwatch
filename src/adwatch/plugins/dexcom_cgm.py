"""Dexcom Continuous Glucose Monitor (CGM) BLE advertisement parser.

Dexcom CGM transmitters (G6, G7, ONE) advertise over BLE to relay glucose
readings to a paired receiver or phone app. They use a proprietary 128-bit
service UUID for CGM data and the standard 180A Device Information Service.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

DEXCOM_SERVICE_UUID = "61ce1c20-e8bc-4287-91fd-7cc25f0df500"
DEVICE_INFO_UUID = "180a"
DEXCOM_NAME_RE = re.compile(r"^(DEX|Dexcom)")


@register_parser(
    name="dexcom_cgm",
    service_uuid=DEXCOM_SERVICE_UUID,
    local_name_pattern=r"^(DEX|Dexcom)",
    description="Dexcom CGM transmitter advertisements",
    version="1.0.0",
    core=False,
)
class DexcomCgmParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = DEXCOM_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and DEXCOM_NAME_RE.match(
            raw.local_name
        )

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Detect model generation from name pattern
        if raw.local_name:
            if raw.local_name == "DEX":
                metadata["model"] = "G7/ONE"
            elif DEXCOM_NAME_RE.match(raw.local_name):
                metadata["model"] = "G6"

        if DEVICE_INFO_UUID in (raw.service_uuids or []):
            metadata["has_device_info"] = True

        return ParseResult(
            parser_name="dexcom_cgm",
            beacon_type="dexcom_cgm",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
