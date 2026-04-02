"""Razer gaming peripheral BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

RAZER_SERVICE_UUID = "fd65"
RAZER_NAME_RE = re.compile(r"^Razer\s+(.+)")


@register_parser(
    name="razer",
    service_uuid=RAZER_SERVICE_UUID,
    local_name_pattern=r"^Razer\s",
    description="Razer gaming peripheral advertisements",
    version="1.0.0",
    core=False,
)
class RazerBleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = (RAZER_SERVICE_UUID in (raw.service_uuids or [])) or \
                     (raw.service_data and RAZER_SERVICE_UUID in raw.service_data)
        name_match = raw.local_name is not None and RAZER_NAME_RE.search(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:razer".encode()
        ).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
            m = RAZER_NAME_RE.match(raw.local_name)
            if m:
                metadata["product"] = m.group(1)

        return ParseResult(
            parser_name="razer",
            beacon_type="razer",
            device_class="gaming_peripheral",
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
                ("razer", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Razer",
            tab_icon="monitor",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Razer Sightings",
                    data_endpoint="/api/razer/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "product", "rssi_max", "sighting_count"]},
                ),
            ],
        )
