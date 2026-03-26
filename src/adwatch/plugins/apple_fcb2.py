"""Apple FCB2 unknown service presence plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

APPLE_FCB2_UUID = "fcb2"


@register_parser(
    name="apple_fcb2",
    service_uuid=APPLE_FCB2_UUID,
    description="Apple FCB2 (unknown service)",
    version="1.0.0",
    core=False,
)
class AppleFCB2Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = (raw.service_uuids and APPLE_FCB2_UUID in raw.service_uuids) or \
                   (raw.service_data and APPLE_FCB2_UUID in raw.service_data)
        if not has_uuid:
            return None

        payload_hex = ""
        if raw.service_data and APPLE_FCB2_UUID in raw.service_data:
            payload_hex = raw.service_data[APPLE_FCB2_UUID].hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:apple_fcb2".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_fcb2",
            beacon_type="apple_fcb2",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=payload_hex,
            metadata={
                "service": "Apple FCB2 (unknown)",
            },
        )
