"""Qingping (ClearGrass) BLE sensor advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

QINGPING_UUID = "0000cdfd-0000-1000-8000-00805f9b34fb"
MIN_HEADER_LEN = 9  # 6 MAC + 2 device type + 1 frame control

DEVICE_TYPES = {
    0x0C: "CGG1",
    0x10: "CGDK2",
    0x12: "CGH1",
    0x18: "Air Monitor Lite",
}

# TLV object type -> (metadata_key, length, signed, scale)
TLV_DEFS = {
    0x0101: ("temperature", 2, True, 0.1),
    0x0201: ("humidity", 2, False, 0.1),
    0x0801: ("battery", 1, False, None),
    0x1201: ("co2", 2, False, None),
    0x0D01: ("pm25", 2, False, None),
}


@register_parser(
    name="qingping",
    service_uuid=QINGPING_UUID,
    description="Qingping (ClearGrass) Sensors",
    version="1.0.0",
    core=False,
)
class QingpingParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or QINGPING_UUID not in raw.service_data:
            return None

        data = raw.service_data[QINGPING_UUID]
        if len(data) < MIN_HEADER_LEN:
            return None

        mac_bytes = data[0:6]
        device_type_code = struct.unpack_from("<H", data, 6)[0]
        # frame_control = data[8]

        # Parse TLV entries
        metadata: dict[str, str | int | float | bool] = {}
        metadata["device_type"] = DEVICE_TYPES.get(device_type_code, "unknown")

        offset = MIN_HEADER_LEN
        while offset + 3 <= len(data):  # need at least type(2) + length(1)
            tlv_type = struct.unpack_from("<H", data, offset)[0]
            tlv_len = data[offset + 2]
            offset += 3

            if offset + tlv_len > len(data):
                break

            if tlv_type in TLV_DEFS:
                key, expected_len, signed, scale = TLV_DEFS[tlv_type]
                if tlv_len == expected_len:
                    if expected_len == 1:
                        value = data[offset]
                    elif expected_len == 2:
                        fmt = "<h" if signed else "<H"
                        value = struct.unpack_from(fmt, data, offset)[0]
                    if scale is not None:
                        metadata[key] = round(value * scale, 1)
                    else:
                        metadata[key] = value

            offset += tlv_len

        # Must have parsed at least one sensor value
        if len(metadata) <= 1:  # only device_type
            return None

        # MAC from service data (reversed) for identity
        mac_str = ":".join(f"{b:02X}" for b in reversed(mac_bytes))
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
