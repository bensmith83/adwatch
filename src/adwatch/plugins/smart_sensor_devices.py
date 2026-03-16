"""Smart Sensor Devices (BlueBerry) environmental sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SMART_SENSOR_DEVICES_COMPANY_ID = 0x075B

SENSOR_TYPES = {
    0x01: ("temperature", 100),
    0x02: ("humidity", 100),
    0x03: ("pressure", 10),
    0x04: ("light", 1),
    0x05: ("air_quality", 1),
}


@register_parser(
    name="smart_sensor_devices",
    company_id=SMART_SENSOR_DEVICES_COMPANY_ID,
    description="Smart Sensor Devices BlueBerry environmental sensors",
    version="1.0.0",
    core=False,
)
class SmartSensorDevicesParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 6:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != SMART_SENSOR_DEVICES_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 4:
            return None

        sensor_type_byte = payload[0]
        value_raw = struct.unpack_from("<h", payload, 1)[0]
        battery = payload[3]

        if sensor_type_byte in SENSOR_TYPES:
            sensor_name, divisor = SENSOR_TYPES[sensor_type_byte]
            value = value_raw / divisor
        else:
            sensor_name = "unknown"
            value = float(value_raw)

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:smart_sensor_devices".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="smart_sensor_devices",
            beacon_type="smart_sensor_devices",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "sensor_type": sensor_name,
                "value": value,
                "battery": battery,
            },
        )

    def storage_schema(self):
        return None
