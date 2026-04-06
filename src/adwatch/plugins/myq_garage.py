"""Chamberlain/LiftMaster MyQ garage door opener BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

MYQ_COMPANY_ID = 0x0878
MYQ_SERVICE_UUID = "26d91a37-c279-4d0f-96a1-532ce41ce0f6"
MYQ_NAME_RE = re.compile(r"^MyQ-(.+)")


@register_parser(
    name="myq",
    company_id=MYQ_COMPANY_ID,
    service_uuid=MYQ_SERVICE_UUID,
    local_name_pattern=r"^MyQ-",
    description="Chamberlain/LiftMaster MyQ garage door advertisements",
    version="1.0.0",
    core=False,
)
class MyQGarageParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = MYQ_NAME_RE.match(raw.local_name)
        if not m:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:myq".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "device_name": raw.local_name,
            "device_id": m.group(1),
        }

        return ParseResult(
            parser_name="myq",
            beacon_type="myq",
            device_class="garage_door",
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
                ("myq", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="MyQ",
            tab_icon="home",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent MyQ Sightings",
                    data_endpoint="/api/myq/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "device_id", "rssi_max", "sighting_count"]},
                ),
            ],
        )
