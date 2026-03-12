"""Xiaomi MiBeacon BLE advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

MIBEACON_UUID = "fe95"

OBJECT_MOTION_ILLUMINANCE = 0x0003
OBJECT_ILLUMINANCE = 0x0007
OBJECT_SOIL_MOISTURE = 0x0008
OBJECT_SOIL_CONDUCTIVITY = 0x0009
OBJECT_BATTERY_LOW = 0x000A
OBJECT_DOOR_WINDOW = 0x000F
OBJECT_MOTION = 0x1001
OBJECT_NO_MOTION = 0x1002
OBJECT_TEMP = 0x1004
OBJECT_BUTTON = 0x1005
OBJECT_HUMIDITY = 0x1006
OBJECT_DOOR_EVENT = 0x1007
OBJECT_BATTERY = 0x100A
OBJECT_TEMP_HUMIDITY = 0x100D
OBJECT_FORMALDEHYDE = 0x1010
OBJECT_SWITCH_EVENT = 0x1012
OBJECT_CONSUMABLES = 0x1013
OBJECT_FLOOD = 0x1014
OBJECT_SMOKE = 0x1015
OBJECT_GAS = 0x1018


@register_parser(
    name="mibeacon",
    service_uuid=MIBEACON_UUID,
    description="Xiaomi MiBeacon",
    version="1.0.0",
    core=False,
)
class MiBeaconParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or MIBEACON_UUID not in raw.service_data:
            return None

        data = raw.service_data[MIBEACON_UUID]
        if len(data) < 5:
            return None

        frame_control, device_type, frame_counter = struct.unpack_from("<HHB", data, 0)
        offset = 5

        has_mac = bool(frame_control & (1 << 4))
        has_capability = bool(frame_control & (1 << 5))
        has_object = bool(frame_control & (1 << 6))
        encrypted = bool(frame_control & (1 << 7))

        if encrypted:
            return None

        mac_str = None
        if has_mac:
            if offset + 6 > len(data):
                return None
            mac_bytes = data[offset:offset + 6]
            mac_str = ":".join(f"{b:02X}" for b in reversed(mac_bytes))
            offset += 6

        if has_capability:
            offset += 1

        metadata: dict[str, str | int | float | bool] = {
            "device_type": device_type,
            "frame_counter": frame_counter,
        }

        if mac_str:
            metadata["mac"] = mac_str

        if has_object and offset + 3 <= len(data):
            object_id, obj_len = struct.unpack_from("<HB", data, offset)
            offset += 3
            obj_data = data[offset:offset + obj_len]
            metadata["object_id"] = object_id

            if object_id == OBJECT_MOTION_ILLUMINANCE and len(obj_data) >= 4:
                metadata["illuminance"] = struct.unpack_from("<I", obj_data, 0)[0]
            elif object_id == OBJECT_ILLUMINANCE and len(obj_data) >= 3:
                metadata["illuminance"] = int.from_bytes(obj_data[:3], "little")
            elif object_id == OBJECT_SOIL_MOISTURE and len(obj_data) >= 1:
                metadata["soil_moisture"] = obj_data[0]
            elif object_id == OBJECT_SOIL_CONDUCTIVITY and len(obj_data) >= 2:
                metadata["soil_conductivity"] = struct.unpack_from("<H", obj_data, 0)[0]
            elif object_id == OBJECT_BATTERY_LOW and len(obj_data) >= 1:
                metadata["battery"] = obj_data[0]
            elif object_id == OBJECT_DOOR_WINDOW and len(obj_data) >= 1:
                metadata["door_window"] = "closed" if obj_data[0] else "open"
            elif object_id == OBJECT_MOTION:
                metadata["motion"] = True
            elif object_id == OBJECT_NO_MOTION:
                metadata["no_motion"] = True
            elif object_id == OBJECT_TEMP and len(obj_data) >= 2:
                metadata["temperature"] = struct.unpack_from("<h", obj_data, 0)[0] / 10.0
            elif object_id == OBJECT_BUTTON and len(obj_data) >= 2:
                metadata["button_event_type"] = obj_data[0]
                metadata["button_count"] = obj_data[1]
            elif object_id == OBJECT_HUMIDITY and len(obj_data) >= 2:
                metadata["humidity"] = struct.unpack_from("<H", obj_data, 0)[0] / 10.0
            elif object_id == OBJECT_DOOR_EVENT and len(obj_data) >= 1:
                metadata["door_event"] = "closed" if obj_data[0] else "open"
            elif object_id == OBJECT_BATTERY and len(obj_data) >= 1:
                metadata["battery"] = obj_data[0]
            elif object_id == OBJECT_TEMP_HUMIDITY and len(obj_data) >= 4:
                metadata["temperature"] = struct.unpack_from("<h", obj_data, 0)[0] / 10.0
                metadata["humidity"] = struct.unpack_from("<H", obj_data, 2)[0] / 10.0
            elif object_id == OBJECT_FORMALDEHYDE and len(obj_data) >= 2:
                metadata["formaldehyde"] = struct.unpack_from("<H", obj_data, 0)[0] / 100.0
            elif object_id == OBJECT_SWITCH_EVENT and len(obj_data) >= 1:
                metadata["switch_event"] = obj_data[0]
            elif object_id == OBJECT_CONSUMABLES and len(obj_data) >= 1:
                metadata["consumables"] = obj_data[0]
            elif object_id == OBJECT_FLOOD and len(obj_data) >= 1:
                metadata["flood"] = "wet" if obj_data[0] else "dry"
            elif object_id == OBJECT_SMOKE and len(obj_data) >= 1:
                metadata["smoke"] = "smoke" if obj_data[0] else "clear"
            elif object_id == OBJECT_GAS and len(obj_data) >= 1:
                metadata["gas"] = "gas" if obj_data[0] else "clear"

        identity_mac = mac_str or raw.mac_address
        id_hash = hashlib.sha256(identity_mac.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="mibeacon",
            beacon_type="mibeacon",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
