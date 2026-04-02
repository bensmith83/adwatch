"""Danalock smart lock BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

DANALOCK_UUID = "fd92"


@register_parser(
    name="danalock",
    service_uuid=DANALOCK_UUID,
    local_name_pattern=r"^DL-",
    description="Danalock smart lock advertisements",
    version="1.0.0",
    core=False,
)
class DanalockParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = (DANALOCK_UUID in (raw.service_uuids or [])) or \
                     (raw.service_data and DANALOCK_UUID in raw.service_data)
        name_match = raw.local_name is not None and raw.local_name.startswith("DL-")

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:danalock".encode()
        ).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
            if raw.local_name.startswith("DL-"):
                metadata["device_id"] = raw.local_name[3:]

        return ParseResult(
            parser_name="danalock",
            beacon_type="danalock",
            device_class="smart_lock",
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
                ("danalock", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Danalock",
            tab_icon="lock",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Danalock Sightings",
                    data_endpoint="/api/danalock/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
