"""Google Nearby Share / Quick Share BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

NEARBY_SHARE_UUID = "fdf7"
BOSE_COMPANY_ID = 0x0065
BOSE_SERVICE_UUID = "fe78"

DEVICE_TYPE_MAP = {
    0x01: ("phone", "phone"),
    0x02: ("tablet", "tablet"),
    0x03: ("laptop", "laptop"),
    0x04: ("watch", "wearable"),
    0x05: ("tv", "tv"),
    0x06: ("car", "vehicle"),
}


@register_parser(
    name="google_nearby_share",
    service_uuid=NEARBY_SHARE_UUID,
    description="Google Nearby Share / Quick Share",
    version="1.0.0",
    core=False,
)
class GoogleNearbyShareParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or NEARBY_SHARE_UUID not in raw.service_data:
            return None

        # Disambiguate from Bose (which also uses FDF7)
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id == BOSE_COMPANY_ID:
                return None
        if raw.service_data and BOSE_SERVICE_UUID in raw.service_data:
            return None
        if raw.service_uuids and BOSE_SERVICE_UUID in raw.service_uuids:
            return None

        data = raw.service_data[NEARBY_SHARE_UUID]
        if not data:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:google_nearby_share".encode()
        ).hexdigest()[:16]

        device_type_byte = data[-1] if data else None
        device_type_name, device_class = DEVICE_TYPE_MAP.get(
            device_type_byte, ("unknown", "phone")
        )

        return ParseResult(
            parser_name="google_nearby_share",
            beacon_type="google_nearby_share",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "payload_hex": data.hex(),
                "device_type": device_type_name,
            },
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
                ("google_nearby_share", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Nearby Share",
            tab_icon="share-2",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Nearby Share Sightings",
                    data_endpoint="/api/google_nearby_share/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "device_type", "rssi_max", "sighting_count"]},
                ),
            ],
        )
