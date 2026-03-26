"""b-parasite open-source soil sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

BPARASITE_UUID = "181a"


@register_parser(
    name="b_parasite",
    service_uuid=BPARASITE_UUID,
    local_name_pattern=r"^prst",
    description="b-parasite soil sensor",
    version="1.0.0",
    core=False,
)
class BParasiteParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.service_data and BPARASITE_UUID in raw.service_data:
            data = raw.service_data[BPARASITE_UUID]
            return self._parse_service_data(raw, data)
        if raw.local_name and raw.local_name.startswith("prst"):
            return self._presence_only(raw)
        return None

    def _parse_service_data(self, raw, data):
        if len(data) < 10:
            return None
        proto = data[0]
        version = (proto >> 4) & 0x0F
        if version != 2:
            return None
        has_light = bool(proto & 0x01)
        battery_mv = struct.unpack(">H", data[2:4])[0]
        temperature = struct.unpack(">h", data[4:6])[0] / 100.0
        humidity = struct.unpack(">H", data[6:8])[0] / 65535.0 * 100.0
        soil_moisture = struct.unpack(">H", data[8:10])[0] / 65535.0 * 100.0

        metadata = {
            "battery_mv": battery_mv,
            "temperature_c": round(temperature, 2),
            "humidity_percent": round(humidity, 2),
            "soil_moisture_percent": round(soil_moisture, 2),
        }
        if has_light and len(data) >= 18:
            metadata["illuminance"] = struct.unpack(">H", data[16:18])[0]

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="b_parasite",
            beacon_type="b_parasite",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def _presence_only(self, raw):
        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="b_parasite",
            beacon_type="b_parasite",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata={"presence_only": True},
        )
