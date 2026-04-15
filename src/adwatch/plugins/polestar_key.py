"""Polestar / Volvo Digital Key BLE advertisement parser.

Polestar and Volvo vehicles advertise over BLE for their Digital Key
system, allowing the phone app to detect proximity and unlock/start
the car. Uses a proprietary 128-bit service UUID.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

POLESTAR_SERVICE_UUID = "bf327664-cc10-9e54-5dd4-41c88fb4f257"
POLESTAR_NAME_RE = re.compile(r"^(Polestar|Volvo)")
MODEL_RE = re.compile(r"^Polestar(\d+)$")


@register_parser(
    name="polestar_key",
    service_uuid=POLESTAR_SERVICE_UUID,
    local_name_pattern=r"^(Polestar|Volvo)",
    description="Polestar/Volvo digital key advertisements",
    version="1.0.0",
    core=False,
)
class PolestarKeyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = POLESTAR_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and POLESTAR_NAME_RE.match(
            raw.local_name
        )

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
            m = MODEL_RE.match(raw.local_name)
            if m:
                metadata["model"] = f"Polestar {m.group(1)}"

        return ParseResult(
            parser_name="polestar_key",
            beacon_type="polestar_digital_key",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
