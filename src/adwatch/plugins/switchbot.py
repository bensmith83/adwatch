"""SwitchBot BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SWITCHBOT_UUID = "0000fd3d-0000-1000-8000-00805f9b34fb"

# device_type_byte -> (name, device_class, min_bytes)
DEVICE_TYPES = {
    0x54: ("meter", "sensor", 5),
    0x48: ("bot", "switch", 3),
    0x63: ("curtain", "cover", 4),
    0x64: ("contact_sensor", "sensor", 3),
    0x73: ("motion_sensor", "sensor", 3),
    0x6A: ("plug_mini", "switch", 4),
    0x6F: ("lock", "lock", 4),
    0x65: ("humidifier", "appliance", 4),
    0x75: ("color_bulb", "light", 3),
    0x3C: ("blind_tilt", "cover", 4),
    0x77: ("hub2", "sensor", 5),
    0x69: ("outdoor_meter", "sensor", 5),
}


@register_parser(
    name="switchbot",
    service_uuid=SWITCHBOT_UUID,
    company_id=0x0969,
    local_name_pattern=r"^W",
    description="SwitchBot",
    version="1.0.0",
    core=False,
)
class SwitchBotParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        payload = raw.service_data.get(SWITCHBOT_UUID)
        if payload is None or len(payload) < 2:
            return None

        dev_byte = payload[0]
        info = DEVICE_TYPES.get(dev_byte)
        if info is None:
            return None

        dev_type, device_class, min_len = info
        if len(payload) < min_len:
            return None

        metadata = {"device_type": dev_type}

        if dev_type == "meter":
            self._parse_meter(payload, metadata)
        elif dev_type == "bot":
            self._parse_bot(payload, metadata)
        elif dev_type == "curtain":
            self._parse_curtain(payload, metadata)
        elif dev_type == "contact_sensor":
            self._parse_contact(payload, metadata)
        elif dev_type == "motion_sensor":
            self._parse_motion(payload, metadata)
        elif dev_type == "plug_mini":
            self._parse_plug_mini(payload, metadata)
        elif dev_type == "lock":
            self._parse_lock(payload, metadata)
        elif dev_type == "humidifier":
            self._parse_humidifier(payload, metadata)
        elif dev_type == "color_bulb":
            self._parse_color_bulb(payload, metadata)
        elif dev_type == "blind_tilt":
            self._parse_blind_tilt(payload, metadata)
        elif dev_type == "hub2":
            self._parse_hub2(payload, metadata)
        elif dev_type == "outdoor_meter":
            self._parse_outdoor_meter(payload, metadata)

        return ParseResult(
            parser_name="switchbot",
            beacon_type="switchbot",
            device_class=device_class,
            identifier_hash=hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16],
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def _parse_meter(self, data: bytes, meta: dict) -> None:
        sign = (data[1] >> 7) & 1
        temp_int = data[1] & 0x7F
        temp_dec = data[2] & 0x0F
        temp = temp_int + temp_dec / 10
        if sign:
            temp = -temp
        meta["temperature_c"] = temp
        meta["humidity_percent"] = data[3]
        meta["battery_percent"] = data[4]

    def _parse_bot(self, data: bytes, meta: dict) -> None:
        meta["mode"] = "switch" if (data[1] >> 7) & 1 else "press"
        meta["state"] = "on" if (data[1] >> 6) & 1 else "off"
        meta["battery_percent"] = data[2]

    def _parse_curtain(self, data: bytes, meta: dict) -> None:
        meta["calibrated"] = bool((data[1] >> 7) & 1)
        meta["position"] = data[1] & 0x7F
        meta["moving"] = bool((data[2] >> 7) & 1)
        if meta["moving"]:
            meta["direction"] = "closing" if (data[2] >> 6) & 1 else "opening"
        if data[3] != 0xFF:
            meta["battery_percent"] = data[3]

    def _parse_contact(self, data: bytes, meta: dict) -> None:
        meta["contact"] = "open" if (data[1] >> 1) & 1 else "closed"
        meta["motion"] = bool(data[1] & 1)
        meta["battery_percent"] = data[2]

    def _parse_motion(self, data: bytes, meta: dict) -> None:
        meta["motion"] = bool(data[1] & 1)
        meta["led_enabled"] = bool((data[1] >> 1) & 1)
        meta["battery_percent"] = data[2]

    def _parse_plug_mini(self, data: bytes, meta: dict) -> None:
        meta["power_state"] = "on" if (data[1] >> 7) & 1 else "off"
        meta["watts"] = data[2]
        meta["overload"] = bool(data[3] & 1)

    def _parse_lock(self, data: bytes, meta: dict) -> None:
        lock_val = (data[1] >> 6) & 0x03
        lock_map = {0: "locked", 1: "unlocked", 2: "jammed"}
        meta["lock_state"] = lock_map.get(lock_val, "unknown")
        meta["door_state"] = "open" if (data[1] >> 5) & 1 else "closed"
        meta["battery_percent"] = data[2]

    def _parse_humidifier(self, data: bytes, meta: dict) -> None:
        meta["power"] = "on" if (data[1] >> 7) & 1 else "off"
        mode_val = (data[1] >> 4) & 0x07
        mode_map = {0: "auto", 1: "low", 2: "med", 3: "high"}
        meta["mode"] = mode_map.get(mode_val, "unknown")
        meta["humidity_setting"] = data[2]
        meta["water_low"] = bool((data[3] >> 7) & 1)

    def _parse_color_bulb(self, data: bytes, meta: dict) -> None:
        meta["power"] = "on" if (data[1] >> 7) & 1 else "off"
        meta["brightness"] = data[1] & 0x7F
        color_val = (data[2] >> 6) & 0x03
        color_map = {0: "white", 1: "color", 2: "scene"}
        meta["color_mode"] = color_map.get(color_val, "unknown")

    def _parse_blind_tilt(self, data: bytes, meta: dict) -> None:
        meta["calibrated"] = bool((data[1] >> 7) & 1)
        meta["position"] = data[1] & 0x7F
        meta["direction"] = "down" if (data[2] >> 6) & 1 else "up"

    def _parse_hub2(self, data: bytes, meta: dict) -> None:
        sign = (data[1] >> 7) & 1
        temp_int = data[1] & 0x7F
        temp_dec = data[2] & 0x0F
        temp = temp_int + temp_dec / 10
        if sign:
            temp = -temp
        meta["temperature_c"] = temp
        meta["humidity_percent"] = data[3]
        meta["light_level"] = data[4]

    def _parse_outdoor_meter(self, data: bytes, meta: dict) -> None:
        sign = (data[1] >> 7) & 1
        temp_int = data[1] & 0x7F
        temp_dec = data[2] & 0x0F
        temp = temp_int + temp_dec / 10
        if sign:
            temp = -temp
        meta["temperature_c"] = temp
        meta["humidity_percent"] = data[3]
        meta["battery_percent"] = data[4]
