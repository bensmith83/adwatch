"""Jieli Audio chipset BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

JIELI_COMPANY_ID = 0x05D6


@register_parser(
    name="jieli_audio",
    company_id=JIELI_COMPANY_ID,
    description="Jieli Audio chipset advertisements",
    version="1.0.0",
    core=False,
)
class JieliAudioParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 3:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != JIELI_COMPANY_ID:
            return None

        version = raw.manufacturer_data[2]
        payload = raw.manufacturer_data[2:]

        id_hash = hashlib.sha256(f"jieli_audio:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {"version": version}

        if raw.local_name:
            metadata["device_name"] = raw.local_name
            # Extract brand as first word from local_name
            brand = raw.local_name.split()[0] if raw.local_name else None
            if brand:
                metadata["brand"] = brand

        return ParseResult(
            parser_name="jieli_audio",
            beacon_type="jieli_audio",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
