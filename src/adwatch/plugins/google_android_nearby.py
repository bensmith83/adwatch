"""Google Android Nearby BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

FRAME_TYPES = {
    0x4a17: "long",
    0x1101: "short",
    0x1102: "short_extended",
}


@register_parser(
    name="google_android_nearby",
    service_uuid="fef3",
    description="Google Android Nearby sharing advertisements",
    version="1.0.0",
    core=False,
)
class GoogleAndroidNearbyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or "fef3" not in raw.service_data:
            return None

        data = raw.service_data["fef3"]
        if not isinstance(data, (bytes, bytearray)):
            data = bytes.fromhex(data)

        if len(data) < 2:
            return None

        magic = int.from_bytes(data[0:2], "big")
        magic_hex = data[0:2].hex()
        frame_type = FRAME_TYPES.get(magic, "unknown")

        id_hash = hashlib.sha256(f"google_android_nearby:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata = {
            "frame_type": frame_type,
            "magic": magic_hex,
            "data_length": len(data),
        }

        return ParseResult(
            parser_name="google_android_nearby",
            beacon_type="google_android_nearby",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
