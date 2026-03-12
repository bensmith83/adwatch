"""Estimote beacon BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

ESTIMOTE_UUID = "fe9a"

FRAME_TYPE_NAMES = {
    1: "nearable",
    2: "telemetry",
}


@register_parser(
    name="estimote",
    service_uuid=ESTIMOTE_UUID,
    description="Estimote beacon advertisements",
    version="1.0.0",
    core=False,
)
class EstimoteParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or ESTIMOTE_UUID not in raw.service_data:
            return None

        data = raw.service_data[ESTIMOTE_UUID]
        if not data:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{data.hex()}".encode()
        ).hexdigest()[:16]

        frame_type = data[0] & 0x0F
        protocol_version = (data[0] & 0xF0) >> 4
        frame_type_name = FRAME_TYPE_NAMES.get(frame_type, "unknown")
        short_identifier = data[1:9].hex() if len(data) >= 9 else None

        return ParseResult(
            parser_name="estimote",
            beacon_type="estimote",
            device_class="beacon",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "payload_hex": data.hex(),
                "payload_length": len(data),
                "protocol_version": protocol_version,
                "frame_type": frame_type,
                "frame_type_name": frame_type_name,
                "short_identifier": short_identifier,
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
                ("estimote", limit),
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
            tab_name="Estimote",
            tab_icon="radio",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Estimote Sightings",
                    data_endpoint="/api/estimote/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "short_identifier", "frame_type_name", "protocol_version", "rssi_max", "sighting_count"]},
                ),
            ],
        )
