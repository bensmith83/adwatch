"""ATC/PVVX custom firmware thermometer plugin.

Supports ATC1.1 (13-15 bytes, big-endian) and PVVX extended (18 bytes, little-endian).
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SVC_UUID = "181a"


@register_parser(
    name="atc_pvvx",
    service_uuid=SVC_UUID,
    description="ATC/PVVX custom firmware thermometers",
    version="1.0.0",
    core=False,
)
class AtcPvvxParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        data = raw.service_data.get(SVC_UUID)
        if not data or len(data) < 13:
            return None

        if len(data) >= 18:
            return self._parse_pvvx(raw, data)
        else:
            return self._parse_atc(raw, data)

    def _parse_atc(self, raw, data):
        # ATC1.1: 6 MAC + int16 BE temp + uint16 BE hum + uint16 BE batt_mv + pct + counter + flags
        temp_raw = struct.unpack_from(">h", data, 6)[0]
        humidity_raw = struct.unpack_from(">H", data, 8)[0]
        battery_mv = struct.unpack_from(">H", data, 10)[0]
        battery_pct = data[12]

        return self._build_result(raw, data, "atc",
                                   temp_raw / 100.0, humidity_raw / 100.0,
                                   battery_mv, battery_pct)

    def _parse_pvvx(self, raw, data):
        # PVVX: 6 MAC + int16 LE temp + uint16 LE hum + uint16 LE batt_mv + pct + counter + flags + reserved + trigger
        temp_raw = struct.unpack_from("<h", data, 6)[0]
        humidity_raw = struct.unpack_from("<H", data, 8)[0]
        battery_mv = struct.unpack_from("<H", data, 10)[0]
        battery_pct = data[12]

        return self._build_result(raw, data, "pvvx",
                                   temp_raw / 100.0, humidity_raw / 100.0,
                                   battery_mv, battery_pct)

    def _build_result(self, raw, data, fmt, temp_c, humidity, battery_mv, battery_pct):
        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="atc_pvvx",
            beacon_type="atc_pvvx",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "temperature_c": temp_c,
                "humidity": humidity,
                "battery_mv": battery_mv,
                "battery_pct": battery_pct,
                "format": fmt,
            },
        )

    def storage_schema(self):
        return None
