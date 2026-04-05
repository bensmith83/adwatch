"""Molekule air purifier BLE advertisement parser.

Molekule air purifiers advertise with service UUID FE4F and local names
matching MOLEKULE_XXXX. The manufacturer data contains an ASCII-encoded
model and serial number string.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

MOLEKULE_SERVICE_UUID = "FE4F"
MOLEKULE_SERVICE_UUID_FULL = "0000fe4f-0000-1000-8000-00805f9b34fb"
MOLEKULE_NAME_RE = re.compile(r"^MOLEKULE_(\S+)")


@register_parser(
    name="molekule",
    service_uuid=MOLEKULE_SERVICE_UUID,
    local_name_pattern=r"^MOLEKULE_",
    description="Molekule air purifier advertisements",
    version="1.0.0",
    core=False,
)
class MolekuleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = MOLEKULE_SERVICE_UUID_FULL in raw.service_uuids
        name_match = raw.local_name is not None and MOLEKULE_NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"molekule:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["device_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        # Manufacturer data is ASCII model-serial string (possibly with trailing non-ASCII byte)
        if raw.manufacturer_data and len(raw.manufacturer_data) > 2:
            try:
                ascii_str = raw.manufacturer_data.decode("ascii", errors="ignore").rstrip()
                if ascii_str:
                    metadata["serial_info"] = ascii_str
            except Exception:
                pass

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="molekule",
            beacon_type="molekule",
            device_class="air_purifier",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
