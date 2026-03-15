"""Mopeka Pro Check propane tank level sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SENSOR_TYPES = {
    0x03: "pro_check",
    0x05: "pro_plus",
    0x08: "pro_plus_gen2",
}

QUALITY_MAP = {
    0x03: "high",
    0x02: "medium",
    0x01: "low",
    0x00: "no_reading",
}


@register_parser(
    name="mopeka",
    local_name_pattern=r"^M[0-9A-Fa-f]+",
    description="Mopeka Pro Check tank level sensors",
    version="1.0.0",
    core=False,
)
class MopekaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 8:
            return None

        data = raw.manufacturer_data

        hw_id = data[0]
        sensor_type_raw = data[1]
        battery_raw = data[2]
        temp_raw = data[3]
        level_raw = struct.unpack_from("<H", data, 4)[0]
        quality_bits = (data[6] >> 6) & 0x03
        flags = data[7]

        battery_voltage = (battery_raw / 32.0) * 2.0 + 1.5
        temperature = float(temp_raw - 40)
        sensor_type = SENSOR_TYPES.get(sensor_type_raw, "unknown")
        reading_quality = QUALITY_MAP.get(quality_bits, "no_reading")
        sync_pressed = bool(flags & 0x01)

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:mopeka".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="mopeka",
            beacon_type="mopeka",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "tank_level_raw": level_raw,
                "temperature": temperature,
                "battery_voltage": battery_voltage,
                "reading_quality": reading_quality,
                "sync_pressed": sync_pressed,
                "sensor_type": sensor_type,
            },
        )

    def storage_schema(self):
        return None
