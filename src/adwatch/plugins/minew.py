"""Minew Technologies industrial BLE beacon/sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

MINEW_COMPANY_ID = 0x0639


@register_parser(
    name="minew",
    company_id=MINEW_COMPANY_ID,
    description="Minew industrial BLE beacons and sensors",
    version="1.0.0",
    core=False,
)
class MinewParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != MINEW_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 1:
            return None

        frame_type = payload[0]

        if frame_type == 0xA1:
            return self._parse_info(payload, raw)
        elif frame_type == 0xA2:
            return self._parse_sensor(payload, raw)
        elif frame_type == 0xA3:
            return self._parse_accel(payload, raw)
        else:
            return None

    def _parse_info(self, payload: bytes, raw: RawAdvertisement) -> ParseResult | None:
        # Need: frame(1) + model(1) + mac(6) + battery(1) + firmware(2) = 11 bytes
        if len(payload) < 11:
            return None

        mac_bytes = payload[2:8]
        mac = ":".join(f"{b:02X}" for b in mac_bytes)
        battery = payload[8]
        fw_major, fw_minor = payload[9], payload[10]

        id_hash = hashlib.sha256(f"{mac}:minew".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="minew",
            beacon_type="minew",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "frame_type": "info",
                "mac": mac,
                "battery": battery,
                "firmware_version": f"{fw_major}.{fw_minor}",
            },
        )

    def _parse_sensor(self, payload: bytes, raw: RawAdvertisement) -> ParseResult | None:
        # Need: frame(1) + temp(2) + humidity(2) = 5 bytes
        if len(payload) < 5:
            return None

        temp_raw = struct.unpack_from(">h", payload, 1)[0]
        hum_raw = struct.unpack_from(">H", payload, 3)[0]

        temperature = temp_raw / 256.0
        humidity = hum_raw / 256.0

        id_hash = hashlib.sha256(f"{raw.mac_address}:minew".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="minew",
            beacon_type="minew",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "frame_type": "sensor",
                "temperature": temperature,
                "humidity": humidity,
            },
        )

    def _parse_accel(self, payload: bytes, raw: RawAdvertisement) -> ParseResult | None:
        # Need: frame(1) + x(2) + y(2) + z(2) = 7 bytes
        if len(payload) < 7:
            return None

        accel_x = struct.unpack_from(">h", payload, 1)[0]
        accel_y = struct.unpack_from(">h", payload, 3)[0]
        accel_z = struct.unpack_from(">h", payload, 5)[0]

        id_hash = hashlib.sha256(f"{raw.mac_address}:minew".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="minew",
            beacon_type="minew",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "frame_type": "accelerometer",
                "accel_x": accel_x,
                "accel_y": accel_y,
                "accel_z": accel_z,
            },
        )

    def storage_schema(self):
        return None
