"""Getac rugged barcode scanner BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

GETAC_NAME_RE = re.compile(r"^(BC\d+.*)Getac$")


@register_parser(
    name="getac",
    local_name_pattern=r"Getac$",
    description="Getac rugged barcode scanner advertisements",
    version="1.0.0",
    core=False,
)
class GetacBarcodeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = GETAC_NAME_RE.match(raw.local_name)
        if not m:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:getac".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "device_name": raw.local_name,
            "serial": m.group(1),
        }

        return ParseResult(
            parser_name="getac",
            beacon_type="getac",
            device_class="barcode_scanner",
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
                ("getac", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Getac",
            tab_icon="scan-line",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Getac Sightings",
                    data_endpoint="/api/getac/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "serial", "rssi_max", "sighting_count"]},
                ),
            ],
        )
