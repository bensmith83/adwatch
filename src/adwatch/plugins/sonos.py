"""Sonos speaker BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

SONOS_COMPANY_ID = 0x05A7


@register_parser(
    name="sonos",
    company_id=SONOS_COMPANY_ID,
    description="Sonos speaker advertisements",
    version="1.0.0",
    core=False,
)
class SonosParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != SONOS_COMPANY_ID:
            return None

        data = raw.manufacturer_payload
        if not data:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="sonos",
            beacon_type="sonos",
            device_class="speaker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "payload_hex": data.hex(),
                "payload_length": len(data),
            },
        )

    def storage_schema(self):
        return None

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()
        parser = self

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            rows = await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("sonos", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                mfr_hex = item.get("manufacturer_data_hex")
                if mfr_hex:
                    try:
                        raw = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=bytes.fromhex(mfr_hex),
                            service_data=None,
                        )
                        result = parser.parse(raw)
                        if result:
                            item.update(result.metadata)
                    except (ValueError, KeyError):
                        pass
                enriched.append(item)
            return enriched

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Sonos",
            tab_icon="speaker",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Sonos Sightings",
                    data_endpoint="/api/sonos/recent",
                    render_hints={
                        "columns": ["timestamp", "mac_address", "local_name", "payload_length", "rssi_max", "sighting_count"],
                    },
                ),
            ],
        )
