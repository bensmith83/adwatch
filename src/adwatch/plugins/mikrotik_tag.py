"""MikroTik BLE Tag (TG-BT5-IN/OUT) asset tracking plugin."""

import hashlib
import math
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="mikrotik_tag",
    local_name_pattern=r"^MikroTik",
    description="MikroTik BLE Tag asset trackers",
    version="1.0.0",
    core=False,
)
class MikroTikTagParser:
    # Sensor data size: 3x int16 + int16 + uint16 + uint8 = 11 bytes
    _SENSOR_SIZE = 11

    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 2:
            return None

        version = data[0]
        flags = data[1]
        encrypted = bool(flags & 0x01)

        # Determine sensor data offset based on MAC inclusion
        offset = 2
        if flags & 0x04:  # MAC included
            offset += 6

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:mikrotik_tag".encode()
        ).hexdigest()[:16]

        if encrypted:
            return ParseResult(
                parser_name="mikrotik_tag",
                beacon_type="mikrotik_tag",
                device_class="tracker",
                identifier_hash=id_hash,
                raw_payload_hex=data.hex(),
                metadata={"encrypted": True},
            )

        # Check enough data for sensor fields
        if len(data) < offset + self._SENSOR_SIZE:
            return None

        accel_x, accel_y, accel_z = struct.unpack_from("<hhh", data, offset)
        temp_raw = struct.unpack_from("<h", data, offset + 6)[0]
        uptime = struct.unpack_from("<H", data, offset + 8)[0]
        battery = data[offset + 10]

        temperature = temp_raw / 256.0
        tilt_angle = round(
            math.degrees(math.atan2(math.sqrt(accel_x**2 + accel_y**2), accel_z)),
            1,
        )

        return ParseResult(
            parser_name="mikrotik_tag",
            beacon_type="mikrotik_tag",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "accel_x": accel_x,
                "accel_y": accel_y,
                "accel_z": accel_z,
                "tilt_angle": tilt_angle,
                "temperature": temperature,
                "uptime": uptime,
                "battery": battery,
                "encrypted": False,
            },
        )

    def storage_schema(self):
        return None
