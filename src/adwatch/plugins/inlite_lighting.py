"""in-lite outdoor landscape lighting BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

INLITE_SERVICE_UUID = "fef1"


@register_parser(
    name="inlite",
    service_uuid=INLITE_SERVICE_UUID,
    local_name_pattern=r"^inlitebt",
    description="in-lite outdoor landscape lighting",
    version="1.0.0",
    core=False,
)
class InliteLightingParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = (INLITE_SERVICE_UUID in (raw.service_uuids or [])) or \
                     (raw.service_data and INLITE_SERVICE_UUID in raw.service_data)
        name_match = raw.local_name is not None and raw.local_name.startswith("inlitebt")

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:inlite".encode()
        ).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="inlite",
            beacon_type="inlite",
            device_class="lighting",
            identifier_hash=id_hash,
            raw_payload_hex="",
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
                ("inlite", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="in-lite",
            tab_icon="sun",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent in-lite Sightings",
                    data_endpoint="/api/inlite/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
