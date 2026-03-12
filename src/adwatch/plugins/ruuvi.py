"""Ruuvi RAWv2 (Data Format 5) BLE advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

RUUVI_COMPANY_ID = 0x0499
RAWV2_FORMAT = 0x05
MIN_PAYLOAD_LEN = 18  # format(1) + fields(17) without MAC


@register_parser(
    name="ruuvi",
    company_id=RUUVI_COMPANY_ID,
    description="Ruuvi RAWv2",
    version="1.0.0",
    core=False,
)
class RuuviParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != RUUVI_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        if len(payload) < MIN_PAYLOAD_LEN:
            return None

        if payload[0] != RAWV2_FORMAT:
            return None

        try:
            temperature = struct.unpack_from(">h", payload, 1)[0] * 0.005
            humidity = struct.unpack_from(">H", payload, 3)[0] * 0.0025
            pressure = struct.unpack_from(">H", payload, 5)[0] + 50000
            accel_x = struct.unpack_from(">h", payload, 7)[0]
            accel_y = struct.unpack_from(">h", payload, 9)[0]
            accel_z = struct.unpack_from(">h", payload, 11)[0]
            power_info = struct.unpack_from(">H", payload, 13)[0]
            voltage = (power_info >> 5) + 1600
            tx_power = (power_info & 0x1F) * 2 - 40
            movement_counter = payload[15]
            measurement_sequence = struct.unpack_from(">H", payload, 16)[0]
        except struct.error:
            return None

        # MAC from payload bytes 18-23 if available
        if len(payload) >= 24:
            mac_bytes = payload[18:24]
            mac_str = ":".join(f"{b:02X}" for b in mac_bytes)
            id_hash = hashlib.sha256(mac_str.encode()).hexdigest()[:16]
        else:
            id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ruuvi",
            beacon_type="ruuvi",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "temperature": temperature,
                "humidity": humidity,
                "pressure": pressure,
                "accel_x": accel_x,
                "accel_y": accel_y,
                "accel_z": accel_z,
                "voltage": voltage,
                "tx_power": tx_power,
                "movement_counter": movement_counter,
                "measurement_sequence": measurement_sequence,
            },
        )
