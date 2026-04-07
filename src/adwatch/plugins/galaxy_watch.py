"""Samsung Galaxy Watch BLE advertisement parser.

Samsung Galaxy Watch devices advertise with service UUID FD69
(Bluetooth SIG assigned to Samsung). Service data contains device
identification and state information.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

GALAXY_WATCH_SERVICE_UUID = "fd69"
NAME_RE = re.compile(r"^Galaxy Watch")


@register_parser(
    name="galaxy_watch",
    service_uuid=GALAXY_WATCH_SERVICE_UUID,
    local_name_pattern=r"^Galaxy Watch",
    description="Samsung Galaxy Watch advertisements",
    version="1.0.0",
    core=False,
)
class GalaxyWatchParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = GALAXY_WATCH_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"galaxy_watch:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Extract service data payload
        svc_data = None
        if raw.service_data and GALAXY_WATCH_SERVICE_UUID in raw.service_data:
            svc_data = raw.service_data[GALAXY_WATCH_SERVICE_UUID]
            metadata["payload_hex"] = svc_data.hex()
            metadata["payload_length"] = len(svc_data)

        raw_hex = svc_data.hex() if svc_data else ""

        return ParseResult(
            parser_name="galaxy_watch",
            beacon_type="galaxy_watch",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
