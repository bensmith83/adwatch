"""Xiaogui Scale (baby/body scale) plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="xiaogui_scale",
    local_name_pattern=r"^(Xiaogui|TZC)",
    description="Xiaogui smart scale (baby/body composition)",
    version="1.0.0",
    core=False,
)
class XiaoguiScaleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 5:
            return None

        data = raw.manufacturer_data
        flags = data[0]

        stabilized = bool(flags & 0x01)
        weight_removed = bool(flags & 0x02)
        is_lbs = bool(flags & 0x10)
        impedance_present = bool(flags & 0x20)

        impedance_raw = struct.unpack_from("<H", data, 1)[0]
        weight_raw = struct.unpack_from("<H", data, 3)[0]

        weight = weight_raw / 10.0
        unit = "lbs" if is_lbs else "kg"
        impedance = impedance_raw if impedance_present else None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:xiaogui_scale".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="xiaogui_scale",
            beacon_type="xiaogui_scale",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "weight": weight,
                "unit": unit,
                "stabilized": stabilized,
                "weight_removed": weight_removed,
                "impedance": impedance,
            },
        )

    def storage_schema(self):
        return None
