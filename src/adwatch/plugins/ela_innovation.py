"""ELA Innovation industrial BLE sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ELA_COMPANY_ID = 0x0757


@register_parser(
    name="ela_innovation",
    company_id=ELA_COMPANY_ID,
    description="ELA Innovation industrial sensors",
    version="1.0.0",
    core=False,
)
class ElaInnovationParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        if not payload or len(payload) < 2:
            return None

        frame_type = payload[0]
        frame_counter = payload[1]
        frame_data = payload[2:]

        if frame_type == 0x01:
            return self._parse_sensor(raw, frame_counter, frame_data)
        elif frame_type == 0x02:
            return self._parse_info(raw, frame_counter, frame_data)
        return None

    def _parse_sensor(self, raw, frame_counter, data):
        if len(data) < 5:
            return None
        temp_raw = struct.unpack_from("<h", data, 0)[0]
        humidity_raw = struct.unpack_from("<H", data, 2)[0]
        battery = data[4]

        return ParseResult(
            parser_name="ela_innovation",
            beacon_type="ela_innovation",
            device_class="sensor",
            identifier_hash=self._id_hash(raw.mac_address),
            raw_payload_hex=raw.manufacturer_payload.hex(),
            metadata={
                "temperature": temp_raw / 100.0,
                "humidity": humidity_raw / 100.0,
                "battery": battery,
                "frame_counter": frame_counter,
            },
        )

    def _parse_info(self, raw, frame_counter, data):
        if len(data) < 5:
            return None
        fw = struct.unpack_from(">H", data, 0)[0]
        hw = struct.unpack_from(">H", data, 2)[0]
        model_byte = data[4]

        return ParseResult(
            parser_name="ela_innovation",
            beacon_type="ela_innovation",
            device_class="sensor",
            identifier_hash=self._id_hash(raw.mac_address),
            raw_payload_hex=raw.manufacturer_payload.hex(),
            metadata={
                "firmware_version": f"{(fw >> 8) & 0xFF}.{fw & 0xFF}",
                "hardware_version": f"{(hw >> 8) & 0xFF}.{hw & 0xFF}",
                "model": f"0x{model_byte:02x}",
                "frame_counter": frame_counter,
            },
        )

    @staticmethod
    def _id_hash(mac):
        return hashlib.sha256(f"{mac}:ela_innovation".encode()).hexdigest()[:16]

    def storage_schema(self):
        return None
