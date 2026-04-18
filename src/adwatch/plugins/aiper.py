"""Aiper robotic pool cleaner BLE advertisement parser.

Per apk-ble-hunting/reports/aiper-link_passive.md. Simple name-prefix
detection; only a protocol version byte is readable from mfr data.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="aiper",
    local_name_pattern=r"^Aiper",
    description="Aiper robotic pool cleaners",
    version="1.0.0",
    core=False,
)
class AiperParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if not name.startswith("Aiper"):
            return None

        metadata: dict = {"device_name": name}
        payload = raw.manufacturer_payload
        if payload:
            metadata["protocol_flag"] = payload[0]

        id_hash = hashlib.sha256(f"aiper:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="aiper",
            beacon_type="aiper",
            device_class="pool_cleaner",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
