"""Rivian Phone Key BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

# Rivian Automotive, LLC — BT SIG company ID 0x0941
RIVIAN_COMPANY_ID = 0x0941

# Custom 128-bit service UUID broadcast by Rivian Phone Key
RIVIAN_SERVICE_UUID = "3db57984-b50c-509b-bce5-153071780c83"


@register_parser(
    name="rivian",
    company_id=RIVIAN_COMPANY_ID,
    service_uuid=RIVIAN_SERVICE_UUID,
    local_name_pattern=r"^Rivian Phone Key",
    description="Rivian Phone Key — vehicle access key broadcasting",
    version="1.0.0",
    core=False,
)
class RivianParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Confirm this is actually a Rivian advertisement
        uuid_match = any(
            u.lower() == RIVIAN_SERVICE_UUID for u in (raw.service_uuids or [])
        )
        company_match = raw.company_id == RIVIAN_COMPANY_ID
        name_match = (raw.local_name or "").startswith("Rivian Phone Key")

        if not uuid_match and not company_match and not name_match:
            return None

        metadata: dict = {}

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        payload = raw.manufacturer_payload
        if payload and len(payload) >= 1:
            metadata["payload_len"] = len(payload)

        # Use MAC + local_name for stable identity (phone keys use random
        # addresses but the combination is stable within a session)
        local_name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{local_name}".encode()
        ).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="rivian",
            beacon_type="rivian_phone_key",
            device_class="vehicle_key",
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
                "SELECT *, last_seen AS timestamp FROM raw_advertisements "
                "WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("rivian", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Rivian",
            tab_icon="car",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Rivian Phone Key Sightings",
                    data_endpoint="/api/rivian/recent",
                    render_hints={
                        "columns": [
                            "timestamp",
                            "mac_address",
                            "local_name",
                            "rssi_max",
                            "sighting_count",
                        ]
                    },
                ),
            ],
        )
