"""ThermoBeacon (SensorBlue / Brifit / ORIA / Thermoplus) sensor plugin.

Layout is ground truth from ``reports/watchflower_passive.md`` — WatchFlower is
open source (``src/src/devices/device_thermobeacon.cpp:407-475`` and
``src/docs/thermobeacon-ble-api.md``).  Models: 2ACD3-WS08 / WS07 / WS02.

The device alternates two manufacturer-data frames.  Offsets are relative to
:attr:`RawAdvertisement.manufacturer_payload` (company ID already stripped).

**18-byte live frame**::

    0   2  padding (0x00 0x00)
    2   6  MAC address, reversed
    8   2  battery, uint16 LE, mV  (/1000 -> V)
    10  2  temperature, int16 LE   (/16 -> °C)
    12  2  humidity, uint16 LE     (/16 -> %RH)
    13  4  uptime, int32 LE        (/256 -> s)

The uptime deliberately overlaps the humidity's high byte — that is what the
source does, not a transcription slip.

**20-byte min/max frame**::

    0   1  padding
    1   1  button state (0x80 = pressed)
    2   6  MAC address, reversed
    8   2  max temperature, int16 LE (/16 -> °C)
    10  4  device time of max, int32 LE
    14  2  min temperature, int16 LE (/16 -> °C)
    16  4  device time of min, int32 LE

WatchFlower throws the 20-byte frame away; it is decoded here because the
min/max history is genuinely useful and costs nothing.

Corrections this audit produced over the previous implementation: the MAC sits
at bytes 2-7 (not 0-5), so battery, temperature and humidity were all read from
the wrong offsets and in the wrong order; the temperature is a plain signed
int16 rather than a value needing an ad-hoc 4096 wraparound; and the embedded
MAC — which survives BLE address rotation — now anchors the identity hash.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# The report pins the company ID at 0x0010; 0x0011 is what a number of units
# emit in the wild, so both are accepted.
THERMOBEACON_COMPANY_ID = 0x0010
THERMOBEACON_COMPANY_IDS = (0x0010, 0x0011)

THERMOBEACON_NAME_PATTERN = r"^(TP3\d|Lanyard|ThermoBeacon)"

LIVE_FRAME_LEN = 18
MINMAX_FRAME_LEN = 20

# device_thermobeacon.cpp: mapNumber(battv, 2300, 3100, 0, 100)
BATTERY_MIN_MV = 2300
BATTERY_MAX_MV = 3100


@register_parser(
    name="thermobeacon",
    company_id=THERMOBEACON_COMPANY_IDS,
    local_name_pattern=THERMOBEACON_NAME_PATTERN,
    description="ThermoBeacon temperature/humidity sensors",
    version="2.0.0",
    core=False,
)
class ThermoBeaconParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id not in THERMOBEACON_COMPANY_IDS:
            return None

        payload = raw.manufacturer_payload
        if payload is None or len(payload) not in (LIVE_FRAME_LEN, MINMAX_FRAME_LEN):
            return None

        mac_str = ":".join(f"{b:02X}" for b in reversed(payload[2:8]))
        metadata: dict = {"company_id": company_id, "mac": mac_str}

        if len(payload) == LIVE_FRAME_LEN:
            metadata.update(self._decode_live(payload))
        else:
            metadata.update(self._decode_minmax(payload))

        id_hash = hashlib.sha256(
            f"thermobeacon:{mac_str}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="thermobeacon",
            beacon_type="thermobeacon",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    @staticmethod
    def _decode_live(payload: bytes) -> dict:
        battery_mv = struct.unpack_from("<H", payload, 8)[0]
        temp_raw = struct.unpack_from("<h", payload, 10)[0]
        humidity_raw = struct.unpack_from("<H", payload, 12)[0]
        # Yes, 13 — the uptime overlaps the humidity high byte.
        uptime_raw = struct.unpack_from("<i", payload, 13)[0]

        return {
            "frame_type": "live",
            "battery_mv": battery_mv,
            "battery_v": battery_mv / 1000.0,
            "battery_percent": ThermoBeaconParser._battery_percent(battery_mv),
            "temperature_c": temp_raw / 16.0,
            "humidity": humidity_raw / 16.0,
            "uptime_seconds": uptime_raw // 256,
        }

    @staticmethod
    def _decode_minmax(payload: bytes) -> dict:
        return {
            "frame_type": "minmax",
            "button_pressed": bool(payload[1] & 0x80),
            "temperature_max_c": struct.unpack_from("<h", payload, 8)[0] / 16.0,
            "time_of_max": struct.unpack_from("<i", payload, 10)[0],
            "temperature_min_c": struct.unpack_from("<h", payload, 14)[0] / 16.0,
            "time_of_min": struct.unpack_from("<i", payload, 16)[0],
        }

    @staticmethod
    def _battery_percent(battery_mv: int) -> float:
        span = BATTERY_MAX_MV - BATTERY_MIN_MV
        pct = (battery_mv - BATTERY_MIN_MV) * 100.0 / span
        return round(max(0.0, min(100.0, pct)), 1)

    def storage_schema(self):
        return None
