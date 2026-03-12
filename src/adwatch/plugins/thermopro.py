"""ThermoPro temperature/humidity sensor plugin."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

THERMOPRO_NAME_RE = re.compile(r"^(TP\d{3}[A-Z]?)\s*\(([\dA-Fa-f]{4})\)$")


def speculate_room(temp_c: float, humidity: int) -> str:
    if temp_c < -10:
        return "Freezer"
    elif temp_c < 2:
        return "Fridge"
    elif temp_c < 10:
        return "Garage/Unheated"
    elif 18 <= temp_c <= 24:
        if humidity < 35:
            return "Indoor (dry/heated)"
        elif humidity <= 55:
            return "Indoor (comfortable)"
        else:
            return "Bathroom/Kitchen"
    elif temp_c > 30:
        return "Attic/Hot area"
    else:
        return "Outdoor/Unknown"


@register_parser(
    name="thermopro",
    local_name_pattern=r"^TP\d{3}",
    description="ThermoPro temperature/humidity sensors",
    version="1.0.0",
    core=False,
)
class ThermoProParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = THERMOPRO_NAME_RE.match(raw.local_name)
        if not m:
            return None

        if not raw.manufacturer_data or len(raw.manufacturer_data) < 7:
            return None

        data = raw.manufacturer_data
        temp_lo = data[1]
        temp_hi = data[2]
        humidity = data[3]

        raw_temp = (temp_hi << 8) | temp_lo
        if raw_temp >= 0x8000:
            raw_temp -= 0x10000
        temperature_c = raw_temp / 10.0

        model = m.group(1)
        room = speculate_room(temperature_c, humidity)

        id_hash = hashlib.sha256(
            f"thermopro:{raw.local_name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="thermopro",
            beacon_type="thermopro",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "temperature_c": temperature_c,
                "humidity": humidity,
                "model": model,
                "room_speculation": room,
            },
            event_type="thermopro_reading",
            storage_table="thermopro_sightings",
            storage_row={
                "timestamp": raw.timestamp,
                "mac_address": raw.mac_address,
                "sensor_id": raw.local_name,
                "model_code": model,
                "temperature_c": temperature_c,
                "humidity": humidity,
                "room_speculation": room,
                "identifier_hash": id_hash,
                "rssi": raw.rssi,
                "raw_payload_hex": data.hex(),
            },
        )

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS thermopro_sightings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    model_code TEXT NOT NULL,
    temperature_c REAL NOT NULL,
    humidity INTEGER NOT NULL,
    room_speculation TEXT NOT NULL,
    identifier_hash TEXT NOT NULL,
    rssi INTEGER,
    raw_payload_hex TEXT
);"""

    def storage_schemas(self) -> list[str]:
        """Return all schema statements for this plugin."""
        schemas = []
        base = self.storage_schema()
        if base:
            schemas.append(base)
        schemas.append("""CREATE TABLE IF NOT EXISTS thermopro_nicknames (
    sensor_id TEXT PRIMARY KEY,
    nickname TEXT NOT NULL
);""")
        return schemas

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter
        from pydantic import BaseModel

        router = APIRouter()
        _nicknames_ensured = False

        class NicknameRequest(BaseModel):
            sensor_id: str
            nickname: str

        async def _ensure_nicknames_table():
            nonlocal _nicknames_ensured
            if not _nicknames_ensured:
                await db.execute(
                    """CREATE TABLE IF NOT EXISTS thermopro_nicknames (
                        sensor_id TEXT PRIMARY KEY,
                        nickname TEXT NOT NULL
                    )"""
                )
                _nicknames_ensured = True

        @router.get("/active")
        async def active_sensors(timeout_minutes: int | None = None):
            await _ensure_nicknames_table()
            if timeout_minutes and timeout_minutes > 0:
                return await db.fetchall(
                    """SELECT s.*, n.nickname
                       FROM thermopro_sightings s
                       LEFT JOIN thermopro_nicknames n ON s.sensor_id = n.sensor_id
                       WHERE s.id IN (
                           SELECT MAX(id) FROM thermopro_sightings GROUP BY sensor_id
                       )
                       AND REPLACE(s.timestamp, 'T', ' ') > datetime('now', ?)
                       ORDER BY s.timestamp DESC""",
                    (f"-{timeout_minutes} minutes",),
                )
            return await db.fetchall(
                """SELECT s.*, n.nickname
                   FROM thermopro_sightings s
                   LEFT JOIN thermopro_nicknames n ON s.sensor_id = n.sensor_id
                   WHERE s.id IN (
                       SELECT MAX(id) FROM thermopro_sightings GROUP BY sensor_id
                   )
                   ORDER BY s.timestamp DESC"""
            )

        @router.put("/nickname")
        async def put_nickname(req: NicknameRequest):
            await _ensure_nicknames_table()
            await db.execute(
                """INSERT INTO thermopro_nicknames (sensor_id, nickname)
                   VALUES (?, ?)
                   ON CONFLICT(sensor_id) DO UPDATE SET nickname = excluded.nickname""",
                (req.sensor_id, req.nickname),
            )
            return {"sensor_id": req.sensor_id, "nickname": req.nickname}

        return router

    def ui_config(self) -> PluginUIConfig | None:
        return PluginUIConfig(
            tab_name="ThermoPro",
            tab_icon="thermometer",
            widgets=[
                WidgetConfig(
                    widget_type="sensor_card",
                    title="Active Sensors",
                    data_endpoint="/api/thermopro/active",
                    config={
                        "fields": ["temperature_c", "humidity", "room_speculation"],
                        "actions": ["nickname"],
                    },
                    render_hints={
                        "primary_field": "temperature_c",
                        "secondary_field": "humidity",
                        "badge_fields": ["room_speculation", "model_code"],
                        "unit": "temperature",
                    },
                ),
            ],
            refresh_interval=30,
        )
