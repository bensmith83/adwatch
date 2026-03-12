"""Matter commissioning BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

MATTER_UUID = "fff6"


@register_parser(
    name="matter",
    service_uuid=MATTER_UUID,
    description="Matter commissioning advertisements",
    version="1.0.0",
    core=False,
)
class MatterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or MATTER_UUID not in raw.service_data:
            return None

        data = raw.service_data[MATTER_UUID]
        if not data or len(data) < 8:
            return None

        opcode = data[0]
        if opcode != 0x01:
            return None

        raw_disc = int.from_bytes(data[1:3], "little")
        discriminator = raw_disc & 0xFFF
        vendor_id = int.from_bytes(data[3:5], "little")
        product_id = int.from_bytes(data[5:7], "little")
        flags = data[7]

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{discriminator:03x}:{vendor_id:04x}:{product_id:04x}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="matter",
            beacon_type="matter_commissioning",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "discriminator": discriminator,
                "vendor_id": vendor_id,
                "product_id": product_id,
                "flags": flags,
            },
            event_type="matter_commissioning",
            storage_table="matter_sightings",
            storage_row={
                "timestamp": raw.timestamp,
                "mac_address": raw.mac_address,
                "discriminator": discriminator,
                "vendor_id": vendor_id,
                "product_id": product_id,
                "flags": flags,
                "identifier_hash": id_hash,
                "rssi": raw.rssi,
                "raw_payload_hex": data.hex(),
            },
        )

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS matter_sightings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    discriminator INTEGER NOT NULL,
    vendor_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    flags INTEGER NOT NULL,
    identifier_hash TEXT NOT NULL,
    rssi INTEGER,
    raw_payload_hex TEXT
);"""

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            return await db.fetchall(
                "SELECT * FROM matter_sightings ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Matter",
            tab_icon="cpu",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Commissioning Ads",
                    data_endpoint="/api/matter/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "discriminator", "vendor_id", "product_id", "flags", "rssi"]},
                ),
            ],
        )
