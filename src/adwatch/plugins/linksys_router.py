"""Linksys WiFi router BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

LINKSYS_UUID = "00002080-8eab-46c2-b788-0e9440016fd1"
BELKIN_COMPANY_ID = 0x005C


@register_parser(
    name="linksys",
    service_uuid=LINKSYS_UUID,
    local_name_pattern=r"^Linksys$",
    description="Linksys WiFi router advertisements",
    version="1.0.0",
    core=False,
)
class LinksysRouterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = (LINKSYS_UUID in (raw.service_uuids or [])) or \
                     (raw.service_data and LINKSYS_UUID in raw.service_data)
        name_match = raw.local_name == "Linksys"

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:linksys".encode()
        ).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="linksys",
            beacon_type="linksys",
            device_class="router",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data[2:].hex() if raw.manufacturer_data and len(raw.manufacturer_data) > 2 else "",
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
                ("linksys", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Linksys",
            tab_icon="wifi",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Linksys Sightings",
                    data_endpoint="/api/linksys/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
