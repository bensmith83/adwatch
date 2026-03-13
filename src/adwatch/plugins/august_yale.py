"""August/Yale smart lock plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="august_yale",
    company_id=[0x01D1, 0x012E, 0x0BDE],
    service_uuid="fe24",
    description="August/Yale smart locks",
    version="1.0.0",
    core=False,
)
class AugustYaleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}

        payload = raw.manufacturer_payload
        if payload and len(payload) >= 1:
            metadata["state_toggle"] = payload[0]

        local_name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{local_name}".encode()
        ).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="august_yale",
            beacon_type="august_yale",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
