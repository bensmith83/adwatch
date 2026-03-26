"""Nut Tracker BLE keyfinder plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="nut_tracker",
    local_name_pattern=r"(?i)^nut",
    description="Nut Tracker keyfinder",
    version="1.0.0",
    core=False,
)
class NutTrackerParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name or not raw.local_name.strip().lower().startswith("nut"):
            return None

        metadata = {
            "device_name": raw.local_name,
            "model": raw.local_name.strip(),
        }

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:nut_tracker".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="nut_tracker",
            beacon_type="nut_tracker",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
