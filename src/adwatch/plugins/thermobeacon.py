"""ThermoBeacon (Brifit/Oria/Thermoplus) temperature/humidity sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

THERMOBEACON_COMPANY_ID = 0x0011


@register_parser(
    name="thermobeacon",
    company_id=THERMOBEACON_COMPANY_ID,
    local_name_pattern=r"^(TP3\d|Lanyard)",
    description="ThermoBeacon temperature/humidity sensors",
    version="1.0.0",
    core=False,
)
class ThermoBeaconParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 14:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != THERMOBEACON_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 12:
            return None

        # Bytes 0-5: MAC (reversed), 6-7: temp, 8-9: humidity, 10-11: battery_mv
        temp_raw = struct.unpack_from("<H", payload, 6)[0]
        humidity_raw = struct.unpack_from("<H", payload, 8)[0]
        battery_mv = struct.unpack_from("<H", payload, 10)[0]

        # Negative temp handling
        if temp_raw > 4000:
            temp_raw = temp_raw - 4096
        temperature_c = temp_raw / 16.0
        humidity = humidity_raw / 16.0

        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="thermobeacon",
            beacon_type="thermobeacon",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "temperature_c": temperature_c,
                "humidity": humidity,
                "battery_mv": battery_mv,
            },
        )

    def storage_schema(self):
        return None
