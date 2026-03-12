"""Tilt Hydrometer BLE advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

APPLE_COMPANY_ID = 0x004C
IBEACON_SUBTYPE = 0x02
IBEACON_LENGTH = 0x15
MIN_PAYLOAD_LEN = 23  # subtype(1) + length(1) + uuid(16) + major(2) + minor(2) + tx(1)

TILT_UUID_PREFIX = bytes.fromhex("A495BB")

TILT_COLORS = {
    0x10: "red",
    0x20: "green",
    0x30: "black",
    0x40: "purple",
    0x50: "orange",
    0x60: "blue",
    0x70: "yellow",
    0x80: "pink",
}


@register_parser(
    name="tilt",
    company_id=APPLE_COMPANY_ID,
    description="Tilt Hydrometer",
    version="1.0.0",
    core=False,
)
class TiltParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != APPLE_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        if len(payload) < MIN_PAYLOAD_LEN:
            return None

        if payload[0] != IBEACON_SUBTYPE or payload[1] != IBEACON_LENGTH:
            return None

        uuid_bytes = payload[2:18]
        if uuid_bytes[:3] != TILT_UUID_PREFIX:
            return None

        color_byte = uuid_bytes[3]
        color = TILT_COLORS.get(color_byte)
        if color is None:
            return None

        uuid_hex = uuid_bytes.hex().upper()
        uuid_str = f"{uuid_hex[:8]}-{uuid_hex[8:12]}-{uuid_hex[12:16]}-{uuid_hex[16:20]}-{uuid_hex[20:]}"

        temp_f = struct.unpack(">H", payload[18:20])[0]
        gravity_x1000 = struct.unpack(">H", payload[20:22])[0]

        temp_c = round((temp_f - 32) * 5 / 9, 1)
        specific_gravity = gravity_x1000 / 1000

        id_hash = hashlib.sha256(uuid_str.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tilt",
            beacon_type="tilt",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "color": color,
                "temperature_f": temp_f,
                "temperature_c": temp_c,
                "specific_gravity": specific_gravity,
                "uuid": uuid_str,
            },
            event_type="tilt_reading",
            storage_table="tilt_readings",
            storage_row={
                "timestamp": raw.timestamp,
                "mac_address": raw.mac_address,
                "color": color,
                "temperature_f": temp_f,
                "temperature_c": temp_c,
                "specific_gravity": specific_gravity,
                "uuid": uuid_str,
                "identifier_hash": id_hash,
                "rssi": raw.rssi,
                "raw_payload_hex": payload.hex(),
            },
        )

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS tilt_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    color TEXT NOT NULL,
    temperature_f INTEGER NOT NULL,
    temperature_c REAL NOT NULL,
    specific_gravity REAL NOT NULL,
    uuid TEXT NOT NULL,
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
        async def active_hydrometers():
            return await db.fetchall(
                """SELECT * FROM tilt_readings
                   WHERE id IN (
                       SELECT MAX(id) FROM tilt_readings GROUP BY color
                   )
                   ORDER BY color"""
            )

        return router

    def ui_config(self) -> PluginUIConfig | None:
        return PluginUIConfig(
            tab_name="Tilt",
            tab_icon="beer",
            widgets=[
                WidgetConfig(
                    widget_type="sensor_card",
                    title="Active Hydrometers",
                    data_endpoint="/api/tilt/active",
                    render_hints={
                        "primary_field": "specific_gravity",
                        "secondary_field": "temperature_f",
                        "badge_fields": ["color", "temperature_c"],
                        "unit": "gravity",
                    },
                ),
            ],
            refresh_interval=30,
        )
