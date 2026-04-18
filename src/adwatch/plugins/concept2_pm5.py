"""Concept2 PM5 rowing computer BLE advertisement parser.

Per apk-ble-hunting/reports/concept2-ergdata_passive.md. Legacy scan API
discards advertisement bytes; detection is name-based.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="concept2_pm5",
    local_name_pattern=r"(?i)PM5|^Concept2",
    description="Concept2 PM5 rowing/ski/bike machine computer",
    version="1.0.0",
    core=False,
)
class Concept2PM5Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if "PM5" not in name and not name.lower().startswith("concept2"):
            return None

        metadata: dict = {"device_name": name}
        id_hash = hashlib.sha256(
            f"concept2:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="concept2_pm5",
            beacon_type="concept2_pm5",
            device_class="fitness_equipment",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
