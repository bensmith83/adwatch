"""UniFi Protect camera BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

UNIFI_UUID = "054e1ac8-1ad8-4c10-a0de-e55fc4f268e5"
UNIFI_NAME_RE = re.compile(r"^UCK")


@register_parser(
    name="unifi_protect",
    service_uuid=UNIFI_UUID,
    local_name_pattern=r"^UCK",
    description="UniFi Protect camera advertisements",
    version="1.0.0",
    core=False,
)
class UniFiProtectParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = UNIFI_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and UNIFI_NAME_RE.search(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"unifi_protect:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="unifi_protect",
            beacon_type="unifi_protect",
            device_class="camera",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
