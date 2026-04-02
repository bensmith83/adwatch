"""Autophix OBD2 automotive diagnostic scanner BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

AUTOPHIX_NAME_RE = re.compile(r"^Autophix\s+(.+)")


@register_parser(
    name="autophix",
    local_name_pattern=r"^Autophix\s",
    description="Autophix OBD2 automotive diagnostic scanner",
    version="1.0.0",
    core=False,
)
class AutophixObd2Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = AUTOPHIX_NAME_RE.match(raw.local_name)
        if not m:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:autophix".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "device_name": raw.local_name,
            "model": m.group(1),
        }

        return ParseResult(
            parser_name="autophix",
            beacon_type="autophix",
            device_class="automotive",
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
                ("autophix", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Autophix",
            tab_icon="truck",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Autophix Sightings",
                    data_endpoint="/api/autophix/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "model", "rssi_max", "sighting_count"]},
                ),
            ],
        )
