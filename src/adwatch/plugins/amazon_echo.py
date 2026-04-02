"""Amazon Echo / Alexa BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

ECHO_NAME_RE = re.compile(r"^Echo\s+(.+)")

ECHO_MODELS = {
    "Pop": "Echo Pop",
    "Dot": "Echo Dot",
    "Show": "Echo Show",
    "Studio": "Echo Studio",
    "Auto": "Echo Auto",
    "Flex": "Echo Flex",
    "Input": "Echo Input",
    "Sub": "Echo Sub",
}


@register_parser(
    name="amazon_echo",
    local_name_pattern=r"^Echo\s",
    description="Amazon Echo / Alexa advertisements",
    version="1.0.0",
    core=False,
)
class AmazonEchoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = ECHO_NAME_RE.match(raw.local_name)
        if not m:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:amazon_echo".encode()
        ).hexdigest()[:16]

        suffix = m.group(1)
        model = "Echo"
        for key in ECHO_MODELS:
            if suffix.startswith(key):
                model = ECHO_MODELS[key]
                break

        metadata: dict = {
            "device_name": raw.local_name,
            "model": model,
        }

        raw_hex = ""
        if raw.service_data and "fe00" in raw.service_data:
            raw_hex = raw.service_data["fe00"].hex()
            metadata["payload_hex"] = raw_hex

        return ParseResult(
            parser_name="amazon_echo",
            beacon_type="amazon_echo",
            device_class="smart_speaker",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
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
                ("amazon_echo", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Echo",
            tab_icon="mic",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Echo Sightings",
                    data_endpoint="/api/amazon_echo/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "model", "rssi_max", "sighting_count"]},
                ),
            ],
        )
