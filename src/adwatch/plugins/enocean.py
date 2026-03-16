"""EnOcean BLE energy-harvesting sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ENOCEAN_COMPANY_ID = 0x03DA

# Expected sensor data sizes (excluding seq + type bytes)
_STM550B_SIZE = 12  # temp(2) + humidity(1) + illum(2) + accel(6) + magnet(1)
_EMDCB_SIZE = 3     # motion(1) + illumination(2)
_PTM216B_SIZE = 1   # button_event(1)


def _parse_stm550b(data: bytes) -> dict:
    temp = struct.unpack_from("<h", data, 0)[0] / 100.0
    humidity = data[2]
    illumination = struct.unpack_from("<H", data, 3)[0]
    accel_x = struct.unpack_from("<h", data, 5)[0]
    accel_y = struct.unpack_from("<h", data, 7)[0]
    accel_z = struct.unpack_from("<h", data, 9)[0]
    magnet = bool(data[11])
    return {
        "sensor_module": "stm550b",
        "temperature": temp,
        "humidity": humidity,
        "illumination": illumination,
        "accel_x": accel_x,
        "accel_y": accel_y,
        "accel_z": accel_z,
        "magnet_contact": magnet,
    }


def _parse_emdcb(data: bytes) -> dict:
    motion = bool(data[0])
    illumination = struct.unpack_from("<H", data, 1)[0]
    return {
        "sensor_module": "emdcb",
        "motion": motion,
        "illumination": illumination,
    }


def _parse_ptm216b(data: bytes) -> dict:
    btn = data[0]
    pressed = bool(btn & 0x01)
    rocker_b = bool(btn & 0x02)
    rocker = "B" if rocker_b else "A"
    action = "press" if pressed else "release"
    return {
        "sensor_module": "ptm216b",
        "button_event": f"rocker_{rocker}_{action}",
    }


_MODULES = {
    0x00: (_STM550B_SIZE, _parse_stm550b),
    0x01: (_EMDCB_SIZE, _parse_emdcb),
    0x02: (_PTM216B_SIZE, _parse_ptm216b),
}


@register_parser(
    name="enocean",
    company_id=ENOCEAN_COMPANY_ID,
    description="EnOcean BLE energy-harvesting sensors",
    version="1.0.0",
    core=False,
)
class EnOceanParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 2:
            return None

        sequence = payload[0]
        event_type = payload[1]
        sensor_data = payload[2:]

        metadata = {"sequence": sequence}

        if event_type in _MODULES:
            expected_size, parse_func = _MODULES[event_type]
            if len(sensor_data) < expected_size:
                metadata["sensor_module"] = "unknown"
            else:
                metadata.update(parse_func(sensor_data[:expected_size]))
                remaining = len(sensor_data) - expected_size
                metadata["authenticated"] = remaining >= 4
        else:
            metadata["sensor_module"] = "unknown"

        if "authenticated" not in metadata:
            metadata["authenticated"] = False

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:enocean".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="enocean",
            beacon_type="enocean",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
