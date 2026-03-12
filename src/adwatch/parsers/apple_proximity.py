"""Apple Proximity Pairing parser (AirPods/Beats)."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

PROXIMITY_TYPE = 0x07

MODEL_NAMES = {
    0x0220: "AirPods 1st Gen",
    0x0F20: "AirPods 2nd Gen",
    0x1320: "AirPods 3rd Gen",
    0x0A20: "AirPods Pro",
    0x1420: "AirPods Pro 2",
    0x0B20: "AirPods Max",
    0x0520: "Beats Solo Pro",
    0x0620: "Beats Studio Buds",
    0x0320: "Powerbeats Pro",
    0x1020: "Beats Fit Pro",
    0x1220: "Beats Studio Buds+",
}


@register_parser(
    name="apple_proximity",
    company_id=0x004C,
    description="Apple Proximity Pairing (AirPods/Beats)",
    version="1.0",
    core=True,
)
class AppleProximityParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        if tlv_type != PROXIMITY_TYPE:
            return None

        tlv_len = data[3]
        tlv_value = data[4:]
        if len(tlv_value) < 7:
            return None

        device_model = (tlv_value[1] << 8) | tlv_value[2]
        utp = tlv_value[3]

        battery_byte1 = tlv_value[4]
        battery_left_raw = (battery_byte1 >> 4) & 0x0F
        battery_right_raw = battery_byte1 & 0x0F

        battery_byte2 = tlv_value[5]
        battery_case_raw = (battery_byte2 >> 4) & 0x0F
        lid_nibble = battery_byte2 & 0x0F

        battery_left = min(battery_left_raw * 10, 100)
        battery_right = min(battery_right_raw * 10, 100)
        battery_case = min(battery_case_raw * 10, 100)

        model_hex = f"{device_model:04x}"
        first_7 = tlv_value[:7]
        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{model_hex}:{first_7.hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_proximity",
            beacon_type="apple_proximity",
            device_class="accessory",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "device_model": device_model,
                "model_name": MODEL_NAMES.get(device_model, "Unknown"),
                "battery_left": battery_left,
                "battery_right": battery_right,
                "battery_case": battery_case,
                "utp": utp,
                "lid_open": lid_nibble != 0,
                "charging_left": bool(utp & 0x01),
                "charging_right": bool(utp & 0x02),
                "charging_case": bool(utp & 0x04),
                "in_ear_left": bool(utp & 0x08),
                "in_ear_right": bool(utp & 0x10),
            },
        )
