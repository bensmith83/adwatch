"""Tuya / Smart Life BLE advertisement plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

TUYA_COMPANY_ID = 0x07D0


@register_parser(
    name="tuya",
    company_id=TUYA_COMPANY_ID,
    description="Tuya / Smart Life BLE advertisements",
    version="1.0.0",
    core=False,
)
class TuyaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != TUYA_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        if len(payload) < 2:
            return None

        protocol_version = payload[0]
        flags = payload[1]
        pairing = bool(flags & 0x01)

        metadata = {
            "protocol_version": protocol_version,
            "flags": flags,
            "pairing": pairing,
        }

        if len(payload) > 2:
            metadata["product_id_hex"] = payload[2:].hex()

        local_name = getattr(raw, "local_name", None)
        if local_name:
            metadata["local_name"] = local_name

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:tuya".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tuya",
            beacon_type="tuya",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
