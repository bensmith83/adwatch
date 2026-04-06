"""ResMed CPAP/sleep device BLE advertisement parser.

ResMed AirSense 11 and related devices advertise with service UUID FD56
(registered to ResMed Ltd) and local names like "ResMed 111682".
The advertisement is a presence beacon — no therapy telemetry is available
from passive scanning.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

RESMED_COMPANY_ID = 0x038D
RESMED_SERVICE_UUID = "fd56"
RESMED_NAME_RE = re.compile(r"^ResMed\s+(\d+)")


@register_parser(
    name="resmed",
    company_id=RESMED_COMPANY_ID,
    service_uuid=RESMED_SERVICE_UUID,
    local_name_pattern=r"^ResMed\s",
    description="ResMed CPAP/sleep device advertisements",
    version="1.0.0",
    core=False,
)
class ResmedParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = any(RESMED_SERVICE_UUID in u for u in raw.service_uuids)
        name_match = raw.local_name and RESMED_NAME_RE.match(raw.local_name)
        company_match = raw.company_id == RESMED_COMPANY_ID

        if not uuid_match and not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:resmed".encode()
        ).hexdigest()[:16]

        metadata: dict = {}

        if name_match:
            metadata["device_number"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        if raw.company_id is not None:
            metadata["company_id"] = f"0x{raw.company_id:04x}"

        if raw.manufacturer_payload:
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        return ParseResult(
            parser_name="resmed",
            beacon_type="resmed",
            device_class="cpap",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
