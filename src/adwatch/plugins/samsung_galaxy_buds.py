"""Samsung Galaxy Buds BLE advertisement parser."""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

BUDS_SERVICE_UUID = "fd69"
BUDS_NAME_RE = re.compile(r"Galaxy Buds")
# Extracts model like "Galaxy Buds3 Pro" from "Galaxy Buds3 Pro (E757) LE"
BUDS_MODEL_RE = re.compile(r"(Galaxy Buds\S*(?:\s+\w+)*?)\s*\(")


@register_parser(
    name="samsung_galaxy_buds",
    service_uuid=BUDS_SERVICE_UUID,
    local_name_pattern=r"Galaxy Buds",
    description="Samsung Galaxy Buds earbuds advertisements",
    version="1.0.0",
    core=False,
)
class SamsungGalaxyBudsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        svc_data = None
        if raw.service_data and BUDS_SERVICE_UUID in raw.service_data:
            svc_data = raw.service_data[BUDS_SERVICE_UUID]

        name_match = raw.local_name and BUDS_NAME_RE.search(raw.local_name)

        if not svc_data and not name_match:
            return None

        metadata: dict = {}

        # Parse fd69 service data fields
        if svc_data and len(svc_data) >= 4:
            metadata["frame_type"] = svc_data[0]
            metadata["device_id"] = int.from_bytes(svc_data[1:3], "big")
            metadata["flags"] = svc_data[3]

        # Extract model from local name
        if raw.local_name:
            m = BUDS_MODEL_RE.search(raw.local_name)
            if m:
                metadata["model"] = m.group(1)

        id_hash = hashlib.sha256(
            f"samsung_galaxy_buds:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        raw_hex = svc_data.hex() if svc_data else ""

        return ParseResult(
            parser_name="samsung_galaxy_buds",
            beacon_type="samsung_galaxy_buds",
            device_class="earbuds",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
