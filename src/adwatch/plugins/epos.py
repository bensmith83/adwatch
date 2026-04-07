"""EPOS audio device BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

EPOS_COMPANY_ID = 0x0082
EPOS_SERVICE_UUID = "63331358-23c1-11e5-b696-feff819cdc9f"


@register_parser(
    name="epos",
    company_id=EPOS_COMPANY_ID,
    service_uuid=EPOS_SERVICE_UUID,
    description="EPOS (Sennheiser) audio device advertisements",
    version="1.0.0",
    core=False,
)
class EposParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        if raw.company_id != EPOS_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload:
            return None

        id_hash = hashlib.sha256(
            f"epos:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
        }

        # Parse payload fields when we have enough data
        # Payload: [state1][state2][device_id_hi][device_id_lo][proto_hi][proto_lo]
        if len(payload) >= 6:
            metadata["state_hex"] = payload[0:2].hex()
            metadata["device_id"] = payload[2:4].hex()
            metadata["protocol_version"] = payload[4:6].hex()

        # Extract model from local name
        if raw.local_name and raw.local_name.startswith("EPOS "):
            metadata["model"] = raw.local_name[5:].strip()

        return ParseResult(
            parser_name="epos",
            beacon_type="epos",
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
                ("epos", limit),
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
            tab_name="EPOS",
            tab_icon="headphones",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent EPOS Sightings",
                    data_endpoint="/api/epos/recent",
                    render_hints={"columns": ["timestamp", "local_name", "model", "device_id", "state_hex", "rssi_max", "sighting_count"]},
                ),
            ],
        )
