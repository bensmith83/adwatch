"""BTHome v2 BLE advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

BTHOME_UUID = "fcd2"

BUTTON_EVENT_MAP = {
    0x00: "none",
    0x01: "press",
    0x02: "double_press",
    0x03: "triple_press",
    0x04: "long_press",
    0x05: "long_double_press",
    0x06: "long_triple_press",
    0x80: "hold_press",
}

# Object ID -> (name, length_bytes, format, scale)
# format: 'u' = unsigned, 's' = signed
OBJECT_DEFS = {
    0x00: ("packet_id", 1, "u", 1),
    0x01: ("battery", 1, "u", 1),
    0x02: ("temperature", 2, "s", 0.01),
    0x03: ("humidity", 2, "u", 0.01),
    0x04: ("pressure", 3, "u", 0.01),
    0x05: ("illuminance", 3, "u", 0.01),
    0x06: ("mass_kg", 2, "u", 0.01),
    0x07: ("mass_lb", 2, "u", 0.01),
    0x08: ("dew_point", 2, "s", 0.01),
    0x09: ("count", 1, "u", 1),
    0x0A: ("energy", 3, "u", 0.001),
    0x0B: ("power", 3, "u", 0.01),
    0x0C: ("voltage", 2, "u", 0.001),
    0x0D: ("pm25", 2, "u", 1),
    0x0E: ("pm10", 2, "u", 1),
    0x0F: ("generic_boolean", 1, "u", 1),
    0x10: ("power_binary", 1, "u", 1),
    0x11: ("opening", 1, "u", 1),
    0x12: ("co2", 2, "u", 1),
    0x13: ("tvoc", 2, "u", 1),
    0x14: ("moisture", 2, "u", 0.01),
    0x15: ("battery_low", 1, "u", 1),
    0x16: ("battery_charging", 1, "u", 1),
    0x17: ("co_detected", 1, "u", 1),
    0x1A: ("door", 1, "u", 1),
    0x1C: ("gas", 1, "u", 1),
    0x1D: ("heat", 1, "u", 1),
    0x1E: ("light", 1, "u", 1),
    0x1F: ("lock", 1, "u", 1),
    0x20: ("moisture_binary", 1, "u", 1),
    0x21: ("motion", 1, "u", 1),
    0x22: ("moving", 1, "u", 1),
    0x23: ("occupancy", 1, "u", 1),
    0x2D: ("window", 1, "u", 1),
    0x2E: ("humidity_flag", 1, "u", 1),
    0x2F: ("moisture_flag", 1, "u", 1),
    0x3A: ("button_event", 1, "u", 1),
    0x3C: ("dimmer_event", 2, "u", 1),
    0x45: ("temperature_01", 2, "s", 0.1),
    0x46: ("uv_index", 1, "u", 0.1),
}


@register_parser(
    name="bthome",
    service_uuid=BTHOME_UUID,
    description="BTHome v2 sensor advertisements",
    version="1.0.0",
    core=False,
)
class BTHomeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or BTHOME_UUID not in raw.service_data:
            return None

        data = raw.service_data[BTHOME_UUID]
        if len(data) < 2:
            return None

        device_info = data[0]
        version = (device_info >> 5) & 0x07
        encrypted = bool(device_info & 0x01)

        if version != 2:
            return None
        if encrypted:
            return None

        metadata: dict[str, str | int | float | bool] = {}
        offset = 1

        while offset < len(data):
            obj_id = data[offset]
            offset += 1

            if obj_id not in OBJECT_DEFS:
                break

            name, length, fmt, scale = OBJECT_DEFS[obj_id]

            if offset + length > len(data):
                break

            obj_bytes = data[offset:offset + length]
            offset += length

            if length == 1:
                value = obj_bytes[0] if fmt == "u" else struct.unpack("<b", obj_bytes)[0]
            elif length == 2:
                value = struct.unpack("<H" if fmt == "u" else "<h", obj_bytes)[0]
            elif length == 3:
                value = int.from_bytes(obj_bytes, "little")
                if fmt == "s" and value >= 0x800000:
                    value -= 0x1000000

            if name == "button_event":
                value = BUTTON_EVENT_MAP.get(value, value)
            elif name == "dimmer_event":
                steps = obj_bytes[0]
                direction = "clockwise" if obj_bytes[1] == 0 else "counter_clockwise"
                metadata[name] = {"steps": steps, "direction": direction}
                continue

            metadata[name] = value * scale if scale != 1 else value

        if not metadata:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="bthome",
            beacon_type="bthome",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
