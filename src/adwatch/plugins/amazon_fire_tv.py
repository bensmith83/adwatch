"""Amazon Fire TV BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="amazon_fire_tv",
    service_uuid="fe00",
    local_name_pattern=r"^Fire TV",
    description="Amazon Fire TV streaming device advertisements",
    version="1.0.0",
    core=False,
)
class AmazonFireTVParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or "fe00" not in raw.service_data:
            return None

        data = raw.service_data["fe00"]
        if not isinstance(data, (bytes, bytearray)):
            data = bytes.fromhex(data)

        if len(data) < 17:
            return None

        header = data[0]
        device_type_code = data[13:17].decode("ascii", errors="replace")

        id_hash = hashlib.sha256(f"amazon_fire_tv:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata = {
            "header": header,
            "device_type_code": device_type_code,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="amazon_fire_tv",
            beacon_type="amazon_fire_tv",
            device_class="streaming_device",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
