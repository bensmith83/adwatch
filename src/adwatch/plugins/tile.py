"""Tile tracker BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

TILE_UUID = "feed"


@register_parser(
    name="tile",
    service_uuid=TILE_UUID,
    description="Tile tracker advertisements",
    version="1.0.0",
    core=False,
)
class TileParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or TILE_UUID not in raw.service_data:
            return None

        data = raw.service_data[TILE_UUID]
        if not data:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{data.hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tile",
            beacon_type="tile",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={"payload_hex": data.hex()},
        )

    def storage_schema(self):
        return None

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            return await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("tile", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Tile",
            tab_icon="map-pin",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Tile Sightings",
                    data_endpoint="/api/tile/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
