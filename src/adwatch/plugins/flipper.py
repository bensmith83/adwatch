"""Flipper Zero multi-tool BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

FLIPPER_UUID = "3081"
FLIPPER_UUID_FULL = "00003081-0000-1000-8000-00805f9b34fb"
FLIPPER_NAME_RE = re.compile(r"^Flipper")


@register_parser(
    name="flipper",
    service_uuid=FLIPPER_UUID,
    local_name_pattern=r"^Flipper",
    description="Flipper Zero multi-tool advertisements",
    version="1.0.0",
    core=False,
)
class FlipperParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Match on service UUID or local name
        uuid_match = FLIPPER_UUID_FULL in raw.service_uuids
        name_match = raw.local_name is not None and FLIPPER_NAME_RE.search(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="flipper",
            beacon_type="flipper",
            device_class="tool",
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
                ("flipper", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Flipper",
            tab_icon="cpu",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Flipper Sightings",
                    data_endpoint="/api/flipper/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
