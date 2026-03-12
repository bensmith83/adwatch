"""Inkbird Sensors BLE advertisement parser (iBBQ / IBS-TH)."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

DISCONNECTED_VALUE = -32768  # 0x8000 signed = probe not connected
MIN_IBBQ_PAYLOAD = 2  # at least 1 probe (2 bytes)
MIN_IBS_TH_PAYLOAD = 4  # temp (2) + humidity (2)


@register_parser(
    name="inkbird",
    service_uuid="0000fff0-0000-1000-8000-00805f9b34fb",
    local_name_pattern=r"^(iBBQ|sps)",
    description="Inkbird Sensors",
    version="1.0.0",
    core=False,
)
class InkbirdParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        try:
            if raw.local_name.startswith("iBBQ"):
                return self._parse_ibbq(raw)
            elif raw.local_name.startswith("sps"):
                return self._parse_ibs_th(raw)
        except struct.error:
            return None

        return None

    def _parse_ibbq(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        payload = raw.manufacturer_data[2:]
        if len(payload) < MIN_IBBQ_PAYLOAD:
            return None

        probe_count = len(payload) // 2
        metadata: dict[str, str | int | float | bool | None] = {
            "device_type": "ibbq",
            "probe_count": probe_count,
        }

        for i in range(probe_count):
            value = struct.unpack_from("<h", payload, i * 2)[0]
            if value == DISCONNECTED_VALUE:
                metadata[f"probe_{i + 1}"] = None
            else:
                metadata[f"probe_{i + 1}"] = value / 10.0

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        storage_row = {
            "timestamp": raw.timestamp,
            "mac_address": raw.mac_address,
            "device_type": "ibbq",
            "temperature": metadata.get("probe_1"),
            "humidity": None,
            "probe_count": probe_count,
            "probe_1": metadata.get("probe_1"),
            "probe_2": metadata.get("probe_2"),
            "probe_3": metadata.get("probe_3"),
            "probe_4": metadata.get("probe_4"),
            "identifier_hash": id_hash,
            "rssi": raw.rssi,
            "raw_payload_hex": payload.hex(),
        }

        return ParseResult(
            parser_name="inkbird",
            beacon_type="inkbird",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
            event_type="inkbird_reading",
            storage_table="inkbird_readings",
            storage_row=storage_row,
        )

    def _parse_ibs_th(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        payload = raw.manufacturer_data[2:]
        if len(payload) < MIN_IBS_TH_PAYLOAD:
            return None

        temp_raw = struct.unpack_from("<h", payload, 0)[0]
        humidity_raw = struct.unpack_from("<H", payload, 2)[0]

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        temperature = temp_raw / 100.0
        humidity = humidity_raw / 100.0

        storage_row = {
            "timestamp": raw.timestamp,
            "mac_address": raw.mac_address,
            "device_type": "ibs_th",
            "temperature": temperature,
            "humidity": humidity,
            "probe_count": 0,
            "probe_1": None,
            "probe_2": None,
            "probe_3": None,
            "probe_4": None,
            "identifier_hash": id_hash,
            "rssi": raw.rssi,
            "raw_payload_hex": payload.hex(),
        }

        return ParseResult(
            parser_name="inkbird",
            beacon_type="inkbird",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "device_type": "ibs_th",
                "temperature": temperature,
                "humidity": humidity,
            },
            event_type="inkbird_reading",
            storage_table="inkbird_readings",
            storage_row=storage_row,
        )

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS inkbird_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    device_type TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    probe_count INTEGER NOT NULL,
    probe_1 REAL,
    probe_2 REAL,
    probe_3 REAL,
    probe_4 REAL,
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
                """SELECT * FROM inkbird_readings
                   WHERE id IN (
                       SELECT MAX(id) FROM inkbird_readings GROUP BY mac_address
                   )
                   ORDER BY timestamp DESC"""
            )

        return router

    def ui_config(self) -> PluginUIConfig | None:
        return PluginUIConfig(
            tab_name="Inkbird",
            tab_icon="flame",
            widgets=[
                WidgetConfig(
                    widget_type="sensor_card",
                    title="Active Sensors",
                    data_endpoint="/api/inkbird/active",
                    render_hints={
                        "primary_field": "temperature",
                        "secondary_field": "humidity",
                        "badge_fields": ["device_type"],
                        "unit": "temperature",
                    },
                ),
            ],
            refresh_interval=30,
        )
