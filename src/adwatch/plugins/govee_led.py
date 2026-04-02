"""Govee LED light strips and bulbs BLE advertisement parser.

Handles Govee LED products (H618A, H6022, H6114, etc.) which are distinct from
Govee temperature/humidity sensors (handled by govee.py with company_id 0xEC88).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

# Match Govee/GBK/ihoment LED product names with model numbers
GOVEE_LED_NAME_RE = re.compile(r"^(?:Govee|GBK|ihoment)_H(\w+)_(\w+)")

# Govee sensor company IDs — if these are present, let the sensor parser handle it
GOVEE_SENSOR_COMPANY_IDS = {0xEC88, 0xEF88}


@register_parser(
    name="govee_led",
    local_name_pattern=r"^(?:Govee|GBK|ihoment)_H",
    description="Govee LED light strips and bulbs",
    version="1.0.0",
    core=False,
)
class GoveeLedParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = GOVEE_LED_NAME_RE.match(raw.local_name)
        if not m:
            return None

        # Don't conflict with the Govee sensor parser — if it has a sensor company_id, skip
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id in GOVEE_SENSOR_COMPANY_IDS:
                return None

        model = f"H{m.group(1)}"
        device_id = m.group(2)

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:govee_led".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "device_name": raw.local_name,
            "model": model,
            "device_id": device_id,
        }

        return ParseResult(
            parser_name="govee_led",
            beacon_type="govee_led",
            device_class="led_light",
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
                ("govee_led", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Govee LED",
            tab_icon="lightbulb",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Govee LED Sightings",
                    data_endpoint="/api/govee_led/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "model", "device_id", "rssi_max", "sighting_count"]},
                ),
            ],
        )
