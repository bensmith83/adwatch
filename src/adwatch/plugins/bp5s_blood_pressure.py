"""iHealth/Andon BP5S blood pressure monitor BLE advertisement parser.

The BP5S advertises with a custom 128-bit service UUID that encodes as ASCII
"com.jiuan.BPV25" (Jiuan is the parent company of iHealth). Company ID 0x0059
is registered to Andon Health Co., Ltd.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

BP5S_COMPANY_ID = 0x0059
BP5S_SERVICE_UUID = "636f6d2e-6a69-7561-6e2e-425056323500"
BP5S_NAME_RE = re.compile(r"^BP5S\s+(\S+)")


@register_parser(
    name="bp5s",
    company_id=BP5S_COMPANY_ID,
    service_uuid=BP5S_SERVICE_UUID,
    local_name_pattern=r"^BP5S\s",
    description="iHealth/Andon BP5S blood pressure monitor advertisements",
    version="1.0.0",
    core=False,
)
class Bp5sParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = any(BP5S_SERVICE_UUID in u for u in raw.service_uuids)
        name_match = raw.local_name and BP5S_NAME_RE.match(raw.local_name)
        company_match = raw.company_id == BP5S_COMPANY_ID

        if not uuid_match and not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:bp5s".encode()
        ).hexdigest()[:16]

        metadata: dict = {}

        if name_match:
            metadata["serial_number"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        if raw.company_id is not None:
            metadata["company_id"] = f"0x{raw.company_id:04x}"

        if raw.manufacturer_payload:
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        return ParseResult(
            parser_name="bp5s",
            beacon_type="bp5s",
            device_class="blood_pressure_monitor",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
