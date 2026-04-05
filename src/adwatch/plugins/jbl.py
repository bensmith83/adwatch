"""JBL speaker BLE advertisement parser.

JBL speakers (owned by Harman/Samsung) advertise with service UUID FDDF
and local names starting with 'JBL '. Some models also include FE2C
service data for Find My Device Network (FMDN) support.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

JBL_SERVICE_UUID = "FDDF"
JBL_SERVICE_UUID_FULL = "0000fddf-0000-1000-8000-00805f9b34fb"
HARMAN_COMPANY_ID = 0x0ECB
JBL_NAME_RE = re.compile(r"^JBL (.+)")


@register_parser(
    name="jbl",
    service_uuid=JBL_SERVICE_UUID,
    local_name_pattern=r"^JBL ",
    description="JBL speaker advertisements",
    version="1.0.0",
    core=False,
)
class JblParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = JBL_SERVICE_UUID_FULL in raw.service_uuids
        name_match = raw.local_name is not None and JBL_NAME_RE.match(raw.local_name)
        fddf_match = raw.service_data and "fddf" in raw.service_data

        if not uuid_match and not name_match and not fddf_match:
            return None

        id_hash = hashlib.sha256(f"jbl:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["model"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        # Check for FMDN (Find My Device Network) via FE2C service data
        if raw.service_data and "fe2c" in raw.service_data:
            fe2c = raw.service_data["fe2c"]
            if fe2c and len(fe2c) > 0:
                metadata["has_fmdn"] = True

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="jbl",
            beacon_type="jbl",
            device_class="speaker",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
