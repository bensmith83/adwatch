"""Google Nearby Presence BLE advertisement parser.

Android devices running Google Play Services advertise with service UUID
FCF1 for device-to-device presence detection. This powers features like
Quick Share discovery, Fast Pair, and Find My Device network coordination.
The payload is encrypted and opaque.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

NEARBY_PRESENCE_UUID = "fcf1"


@register_parser(
    name="google_nearby_presence",
    service_uuid=NEARBY_PRESENCE_UUID,
    description="Google Nearby Presence (Android Play Services)",
    version="1.0.0",
    core=False,
)
class GoogleNearbyPresenceParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or NEARBY_PRESENCE_UUID not in raw.service_data:
            return None

        data = raw.service_data[NEARBY_PRESENCE_UUID]
        if not data:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {
            "payload_length": len(data),
        }

        # First byte is a version indicator
        if len(data) >= 1:
            metadata["version"] = data[0]

        return ParseResult(
            parser_name="google_nearby_presence",
            beacon_type="google_nearby_presence",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
