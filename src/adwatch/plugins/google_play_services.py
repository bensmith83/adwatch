"""Google Play Services BLE presence plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

PLAY_SERVICES_UUID = "fcf1"


@register_parser(
    name="google_play_services",
    service_uuid=PLAY_SERVICES_UUID,
    description="Google Play Services (Android)",
    version="1.0.0",
    core=False,
)
class GooglePlayServicesParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = (raw.service_uuids and PLAY_SERVICES_UUID in raw.service_uuids) or \
                   (raw.service_data and PLAY_SERVICES_UUID in raw.service_data)
        if not has_uuid:
            return None

        payload_hex = ""
        if raw.service_data and PLAY_SERVICES_UUID in raw.service_data:
            payload_hex = raw.service_data[PLAY_SERVICES_UUID].hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:google_play_services".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="google_play_services",
            beacon_type="google_play_services",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=payload_hex,
            metadata={
                "service": "Google Play Services",
            },
        )
