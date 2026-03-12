"""Sensirion MyCO2/MyAmbience gadget plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SVC_UUID = "fe40"


@register_parser(
    name="sensirion",
    service_uuid=SVC_UUID,
    description="Sensirion MyCO2/MyAmbience environmental gadgets",
    version="1.0.0",
    core=False,
)
class SensirionParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        data = raw.service_data.get(SVC_UUID)
        if not data or len(data) < 5:
            return None

        device_type = data[0]
        temp_raw = struct.unpack_from("<h", data, 1)[0]
        humidity_raw = struct.unpack_from("<H", data, 3)[0]

        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        metadata = {
            "device_type": device_type,
            "temperature_c": temp_raw / 100.0,
            "humidity": humidity_raw / 100.0,
        }

        if len(data) >= 7:
            metadata["co2_ppm"] = struct.unpack_from("<H", data, 5)[0]

        return ParseResult(
            parser_name="sensirion",
            beacon_type="sensirion",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
