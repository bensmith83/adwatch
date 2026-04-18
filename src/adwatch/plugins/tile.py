"""Tile tracker BLE advertisement parser.

Identifiers and variants per apk-ble-hunting/reports/thetileapp-tile_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser


# Tile SIG-assigned service UUIDs.
TILE_UUID_LEGACY = "feed"       # legacy format: plain tileId (no rotation)
TILE_UUID_PRIVATEID = "feec"    # current format: rotating hashedId (~15 min)

_TILE_UUIDS = (TILE_UUID_LEGACY, TILE_UUID_PRIVATEID)


@register_parser(
    name="tile",
    service_uuid=list(_TILE_UUIDS),
    description="Tile tracker advertisements",
    version="1.1.0",
    core=False,
)
class TileParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        variant = None
        data = None
        for uuid in _TILE_UUIDS:
            if uuid in raw.service_data and raw.service_data[uuid]:
                data = raw.service_data[uuid]
                variant = "privateid" if uuid == TILE_UUID_PRIVATEID else "legacy"
                break

        if data is None or variant is None:
            return None

        metadata: dict = {
            "payload_hex": data.hex(),
            "variant": variant,
            "service_data_length": len(data),
        }

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{data.hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tile",
            beacon_type="tile",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
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
