"""Efento environmental sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

EFENTO_COMPANY_ID = 0x026C

SENSOR_TYPES = {
    0x01: "temperature_c",
    0x02: "humidity",
    0x03: "pressure",
    0x05: "co2_ppm",
}


@register_parser(
    name="efento",
    company_id=EFENTO_COMPANY_ID,
    description="Efento environmental sensors",
    version="1.0.0",
    core=False,
)
class EfentoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 10:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != EFENTO_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 6:
            return None

        version = payload[0]
        if version != 0x03:
            return None

        serial = payload[1:5].hex()

        # Parse measurement slots: each is 3 bytes (type + int16_le value)
        # Battery is the last byte
        slot_data = payload[5:]
        metadata = {
            "serial": serial,
        }

        pos = 0
        while pos + 3 < len(slot_data):
            sensor_type = slot_data[pos]
            value = struct.unpack_from("<h", slot_data, pos + 1)[0]
            key = SENSOR_TYPES.get(sensor_type)
            if key:
                if key in ("temperature_c", "humidity"):
                    metadata[key] = value / 10.0
                else:
                    metadata[key] = value
            pos += 3

        # Last byte is battery
        if pos < len(slot_data):
            metadata["battery"] = slot_data[pos]

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{serial}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="efento",
            beacon_type="efento",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
