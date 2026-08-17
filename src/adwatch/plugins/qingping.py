"""Qingping / ClearGrass BLE sensor advertisement parser (service data 0xFDCD).

Layout is ground truth from ``reports/watchflower_passive.md`` — WatchFlower is
open source, so ``src/src/device_sensor_advertisement.cpp:401-556`` settles the
format rather than inferring it.

::

    byte 0     frame control
    byte 1     product id
    bytes 2-7  MAC address, reversed (a static, trackable identifier)
    bytes 8+   TLV objects: type(1) + length(1) + data

Two bugs this rewrite fixes:

* The service UUID was registered as ``0000cdfd-…`` — the byte-swapped form.
  Real adverts arrive as ``0xFDCD`` / ``0000fdcd-…``, so the parser could
  never match a live Qingping sensor.
* The TLV loop used a **2-byte** object type starting at offset 9.  Objects
  are keyed by a **1-byte** type and start at offset 8, so every object ID and
  every subsequent offset was wrong.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser, _normalize_uuid

QINGPING_UUID = "0000fdcd-0000-1000-8000-00805f9b34fb"
_QINGPING_UUID_FULL = _normalize_uuid(QINGPING_UUID)

# frame control + product id + 6-byte MAC
HEADER_LEN = 8
TLV_START = 8

DEVICE_TYPES = {
    0x0C: "CGG1",
    0x10: "CGDK2",
    0x12: "CGH1",
    0x18: "Air Monitor Lite",
}

# TLV object type -> handler name.  Scalings per the WatchFlower table.
TLV_TEMP_HUMIDITY = 0x01
TLV_BATTERY = 0x02
TLV_PRESSURE = 0x07
TLV_DOOR_STATE = 0x0F
TLV_PM = 0x12
TLV_CO2 = 0x13


@register_parser(
    name="qingping",
    service_uuid=QINGPING_UUID,
    description="Qingping (ClearGrass) Sensors",
    version="2.0.0",
    core=False,
)
class QingpingParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = self._service_payload(raw)
        if data is None or len(data) < HEADER_LEN:
            return None

        try:
            return self._parse_inner(raw, data)
        except struct.error:
            return None

    @staticmethod
    def _service_payload(raw: RawAdvertisement) -> bytes | None:
        for key, value in (raw.service_data or {}).items():
            if _normalize_uuid(key) == _QINGPING_UUID_FULL:
                return value
        return None

    def _parse_inner(self, raw: RawAdvertisement, data: bytes) -> ParseResult | None:
        frame_control = data[0]
        product_id = data[1]
        mac_bytes = data[2:8]

        metadata: dict[str, str | int | float | bool] = {
            "frame_control": frame_control,
            "product_id": product_id,
            "device_type": DEVICE_TYPES.get(product_id, "unknown"),
        }
        header_keys = len(metadata)

        offset = TLV_START
        while offset + 2 <= len(data):
            tlv_type = data[offset]
            tlv_len = data[offset + 1]
            offset += 2

            if offset + tlv_len > len(data):
                break

            value = data[offset:offset + tlv_len]
            self._decode_tlv(metadata, tlv_type, value)
            offset += tlv_len

        # MAC from service data (reversed) — survives BLE MAC rotation.
        mac_str = ":".join(f"{b:02X}" for b in reversed(mac_bytes))
        metadata["mac"] = mac_str

        # Header fields alone are not a reading.
        if len(metadata) <= header_keys + 1:
            return None

        id_hash = hashlib.sha256(mac_str.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="qingping",
            beacon_type="qingping",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
            event_type="qingping_reading",
            storage_table="qingping_readings",
            storage_row={
                "timestamp": raw.timestamp,
                "mac_address": raw.mac_address,
                "device_type": metadata.get("device_type"),
                "temperature": metadata.get("temperature"),
                "humidity": metadata.get("humidity"),
                "battery": metadata.get("battery"),
                "co2": metadata.get("co2"),
                "pm25": metadata.get("pm25"),
                "identifier_hash": id_hash,
                "rssi": raw.rssi,
                "raw_payload_hex": data.hex(),
            },
        )

    @staticmethod
    def _decode_tlv(metadata: dict, tlv_type: int, value: bytes) -> None:
        if tlv_type == TLV_TEMP_HUMIDITY and len(value) >= 4:
            temp, humi = struct.unpack_from("<hh", value, 0)
            metadata["temperature"] = round(temp / 10.0, 1)
            metadata["humidity"] = round(humi / 10.0, 1)
        elif tlv_type == TLV_BATTERY and len(value) >= 1:
            metadata["battery"] = value[0]
        elif tlv_type == TLV_PRESSURE and len(value) >= 2:
            metadata["pressure"] = round(
                struct.unpack_from("<h", value, 0)[0] / 10.0, 1
            )
        elif tlv_type == TLV_DOOR_STATE and len(value) >= 1:
            metadata["door_state"] = value[0]
        elif tlv_type == TLV_PM and len(value) >= 4:
            pm25, pm10 = struct.unpack_from("<hh", value, 0)
            metadata["pm25"] = pm25
            metadata["pm10"] = pm10
        elif tlv_type == TLV_CO2 and len(value) >= 2:
            metadata["co2"] = struct.unpack_from("<h", value, 0)[0]

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS qingping_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    device_type TEXT,
    temperature REAL,
    humidity REAL,
    battery INTEGER,
    co2 INTEGER,
    pm25 INTEGER,
    identifier_hash TEXT NOT NULL,
    rssi INTEGER,
    raw_payload_hex TEXT
);"""

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter

        router = APIRouter()

        @router.get("/active")
        async def active_sensors():
            return await db.fetchall(
                """SELECT * FROM qingping_readings
                   WHERE id IN (
                       SELECT MAX(id) FROM qingping_readings
                       GROUP BY identifier_hash
                   )
                   ORDER BY timestamp DESC"""
            )

        return router

    def ui_config(self) -> PluginUIConfig | None:
        return PluginUIConfig(
            tab_name="Qingping",
            tab_icon="wind",
            widgets=[
                WidgetConfig(
                    widget_type="sensor_card",
                    title="Active Sensors",
                    data_endpoint="/api/qingping/active",
                    render_hints={
                        "primary_field": "temperature",
                        "secondary_field": "humidity",
                        "badge_fields": ["device_type", "battery"],
                        "unit": "temperature",
                    },
                ),
            ],
            refresh_interval=30,
        )
