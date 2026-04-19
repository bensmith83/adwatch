"""Nest / Google Home BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

NEST_UUID = "feaf"


@register_parser(
    name="nest",
    service_uuid=NEST_UUID,
    description="Nest / Google Home advertisements",
    version="1.0.0",
    core=False,
)
class NestParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = b""
        if raw.service_data:
            for key, value in raw.service_data.items():
                if key.lower() == NEST_UUID and value:
                    data = value
                    break

        has_uuid = any(u.lower() == NEST_UUID for u in (raw.service_uuids or []))
        if not data and not has_uuid:
            return None

        if data:
            id_hash = hashlib.sha256(
                f"{raw.mac_address}:{data.hex()}".encode()
            ).hexdigest()[:16]
        else:
            id_hash = hashlib.sha256(
                f"{raw.mac_address}:{raw.local_name or ''}".encode()
            ).hexdigest()[:16]

        return ParseResult(
            parser_name="nest",
            beacon_type="nest",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "payload_hex": data.hex(),
                "payload_length": len(data),
                "device_code": getattr(raw, "local_name", None),
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
                ("nest", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                svc_json = item.get("service_data_json")
                if svc_json:
                    try:
                        svc_data = deserialize_service_data(svc_json)
                        raw = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=None,
                            service_data=svc_data,
                            local_name=item.get("local_name"),
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
            tab_name="Nest",
            tab_icon="home",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Nest Sightings",
                    data_endpoint="/api/nest/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "payload_hex", "rssi_max", "sighting_count"]},
                ),
            ],
        )
