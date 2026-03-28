"""Shelly BLU sensor BLE advertisement plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SHELLY_COMPANY_ID = 0x0BA9

_MODEL_MAP = {
    "SBBT": "BLU Button",
    "SBDW": "BLU Door/Window",
    "SBMO": "BLU Motion",
    "SBHT": "BLU H&T",
}


@register_parser(
    name="shelly_blu",
    company_id=SHELLY_COMPANY_ID,
    local_name_pattern=r"^SB[A-Z]{2}-",
    description="Shelly BLU sensor advertisements",
    version="1.0.0",
    core=False,
)
class ShellyBluParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 5:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != SHELLY_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        device_type = payload[0]
        packet_counter = payload[1]
        battery_level = payload[2]

        local_name = getattr(raw, "local_name", None)

        if local_name and len(local_name) >= 4:
            prefix = local_name[:4]
            model = _MODEL_MAP.get(prefix, "BLU Unknown")
        else:
            model = "Unknown"

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:shelly_blu".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="shelly_blu",
            beacon_type="shelly_blu",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "device_type": device_type,
                "packet_counter": packet_counter,
                "battery_level": battery_level,
                "model": model,
                "local_name": local_name,
            },
        )

    def storage_schema(self):
        return None
