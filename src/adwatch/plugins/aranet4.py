"""Aranet4 CO2 monitor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ARANET_UUID = "f0cd3001-95da-4f4b-9ac8-aa55d312af0c"

STATUS_NAMES = {0: "green", 1: "yellow", 2: "red"}


@register_parser(
    name="aranet4",
    service_uuid=ARANET_UUID,
    local_name_pattern=r"^Aranet4",
    description="Aranet4 CO2 monitor",
    version="1.0.0",
    core=False,
)
class Aranet4Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        data = raw.service_data.get(ARANET_UUID)
        if not data or len(data) < 13:
            return None

        co2 = struct.unpack_from("<H", data, 0)[0]
        temp_raw = struct.unpack_from("<H", data, 2)[0]
        pressure_raw = struct.unpack_from("<H", data, 4)[0]
        humidity = data[6]
        battery = data[7]
        status = data[8]
        interval = struct.unpack_from("<H", data, 9)[0]
        age = struct.unpack_from("<H", data, 11)[0]

        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="aranet4",
            beacon_type="aranet4",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "co2_ppm": co2,
                "temperature_c": temp_raw / 20.0,
                "pressure_hpa": pressure_raw / 10.0,
                "humidity": humidity,
                "battery": battery,
                "status": STATUS_NAMES.get(status, f"unknown({status})"),
                "interval_s": interval,
                "age_s": age,
            },
        )

    def storage_schema(self):
        return None
