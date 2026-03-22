"""Bose audio device BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

BOSE_COMPANY_ID = 0x0065
BOSE_FEBE_COMPANY_ID = 0x3703
BOSE_SERVICE_UUID_FDF7 = "fdf7"


@register_parser(
    name="bose",
    company_id=BOSE_COMPANY_ID,
    service_uuid=["fe78", "febe"],
    description="Bose audio device advertisements",
    version="1.0.0",
    core=False,
)
class BoseParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        if raw.company_id not in (BOSE_COMPANY_ID, BOSE_FEBE_COMPANY_ID):
            return None

        payload = raw.manufacturer_payload
        if not payload:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
        }

        if raw.service_data and BOSE_SERVICE_UUID_FDF7 in raw.service_data:
            svc_data = raw.service_data[BOSE_SERVICE_UUID_FDF7]
            if svc_data:
                metadata["service_payload_hex"] = svc_data.hex()
                metadata["service_payload_length"] = len(svc_data)

        return ParseResult(
            parser_name="bose",
            beacon_type="bose",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
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
                ("bose", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                mfr_hex = item.get("manufacturer_data_hex")
                if mfr_hex:
                    try:
                        svc_data = None
                        svc_json = item.get("service_data_json")
                        if svc_json:
                            svc_data = deserialize_service_data(svc_json)
                        raw = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=bytes.fromhex(mfr_hex),
                            service_data=svc_data,
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
            tab_name="Bose",
            tab_icon="headphones",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Bose Sightings",
                    data_endpoint="/api/bose/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "payload_length", "rssi_max", "sighting_count"]},
                ),
            ],
        )
