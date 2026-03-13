"""Chipolo tracker tag plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

CHIPOLO_COMPANY_ID = 0x08C3

COLORS = {
    0: "Gray",
    1: "White",
    2: "Black",
    3: "Violet",
    4: "Blue",
    5: "Green",
    6: "Yellow",
    7: "Orange",
    8: "Red",
    9: "Pink",
}


@register_parser(
    name="chipolo",
    company_id=CHIPOLO_COMPANY_ID,
    service_uuid="fe33",
    description="Chipolo tracker tags",
    version="1.0.0",
    core=False,
)
class ChipoloParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}

        # Extract color from service data
        if raw.service_data and "fe33" in raw.service_data:
            svc_data = raw.service_data["fe33"]
            if svc_data and len(svc_data) >= 1:
                color_code = svc_data[0]
                metadata["color_code"] = color_code
                metadata["color"] = COLORS.get(color_code, "Unknown")

        payload = raw.manufacturer_payload
        raw_hex = payload.hex() if payload else ""

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:chipolo".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="chipolo",
            beacon_type="chipolo",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
