"""Meshtastic LoRa mesh node BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

MESHTASTIC_SERVICE_UUID = "6ba1b218-15a8-461f-9fa8-5dcae273eafd"
MESHTASTIC_NAME_RE = re.compile(r"^Meshtastic_(.+)")


@register_parser(
    name="meshtastic",
    service_uuid=MESHTASTIC_SERVICE_UUID,
    local_name_pattern=r"^Meshtastic_",
    description="Meshtastic mesh networking advertisements",
    version="1.0.0",
    core=False,
)
class MeshtasticParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = MESHTASTIC_SERVICE_UUID in raw.service_uuids
        name_match = raw.local_name is not None and MESHTASTIC_NAME_RE.search(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"{raw.mac_address}:meshtastic".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["node_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="meshtastic",
            beacon_type="meshtastic",
            device_class="mesh_node",
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
                ("meshtastic", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Meshtastic",
            tab_icon="radio",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Meshtastic Sightings",
                    data_endpoint="/api/meshtastic/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
