"""Marshall Bluetooth speaker BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

MARSHALL_SERVICE_UUID = "fe8f"
QUALCOMM_COMPANY_ID = 0x0912

KNOWN_MODELS = {
    "STANMORE", "STANMORE II", "STANMORE III",
    "ACTON", "ACTON II", "ACTON III",
    "WOBURN", "WOBURN II", "WOBURN III",
    "EMBERTON", "EMBERTON II",
    "KILBURN", "KILBURN II",
    "MIDDLETON",
    "WILLEN", "WILLEN II",
    "STOCKWELL", "STOCKWELL II",
    "MONITOR", "MONITOR II",
    "MAJOR", "MAJOR IV", "MAJOR V",
    "MINOR", "MINOR III", "MINOR IV",
    "MOTIF", "MOTIF II",
    "MODE", "MODE II",
}


@register_parser(
    name="marshall_audio",
    service_uuid=MARSHALL_SERVICE_UUID,
    description="Marshall Bluetooth speaker advertisements",
    version="1.0.0",
    core=False,
)
class MarshallAudioParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = (MARSHALL_SERVICE_UUID in (raw.service_uuids or [])) or \
                   (raw.service_data and MARSHALL_SERVICE_UUID in raw.service_data)

        if not has_uuid:
            return None

        # Verify it's likely a Marshall by checking local_name or company_id
        name = raw.local_name
        is_marshall = name and any(name.upper().startswith(m) for m in KNOWN_MODELS)
        has_qualcomm = (raw.manufacturer_data and len(raw.manufacturer_data) >= 2 and
                        int.from_bytes(raw.manufacturer_data[:2], "little") == QUALCOMM_COMPANY_ID)

        if not is_marshall and not has_qualcomm:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:marshall_audio".encode()
        ).hexdigest()[:16]

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
            metadata["model"] = name

        return ParseResult(
            parser_name="marshall_audio",
            beacon_type="marshall_audio",
            device_class="speaker",
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
                ("marshall_audio", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Marshall",
            tab_icon="speaker",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Marshall Sightings",
                    data_endpoint="/api/marshall_audio/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "model", "rssi_max", "sighting_count"]},
                ),
            ],
        )
