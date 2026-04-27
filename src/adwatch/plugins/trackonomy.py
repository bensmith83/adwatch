"""Trackonomy Systems BLE advertisement parser.

Trackonomy makes disposable BLE/cellular asset-tracking "smart stickers" used
in shipping and logistics. Detection is by SIG company ID 0x0EF7 only —
payload format is proprietary and varies across SKUs (TrackPack, Wing, etc.).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TRACKONOMY_COMPANY_ID = 0x0EF7


@register_parser(
    name="trackonomy",
    company_id=TRACKONOMY_COMPANY_ID,
    description="Trackonomy Systems BLE/cellular asset trackers",
    version="1.0.0",
    core=False,
)
class TrackonomyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not (raw.manufacturer_data and len(raw.manufacturer_data) >= 2):
            return None
        if int.from_bytes(raw.manufacturer_data[:2], "little") != TRACKONOMY_COMPANY_ID:
            return None

        metadata: dict = {
            "company_id_hex": f"0x{TRACKONOMY_COMPANY_ID:04X}",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"trackonomy:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="trackonomy",
            beacon_type="trackonomy",
            device_class="asset_tracker",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )
