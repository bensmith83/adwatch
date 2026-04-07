"""SleepTracker (Beautyrest/Fullpower) BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

SLEEPTRACKER_COMPANY_ID = 0x01EF
SLEEPTRACKER_SERVICE_UUID = "f6380280-6d90-442c-8feb-3aec76948f06"


@register_parser(
    name="sleeptracker",
    company_id=SLEEPTRACKER_COMPANY_ID,
    service_uuid=SLEEPTRACKER_SERVICE_UUID,
    local_name_pattern=r"^SleepTracker$",
    description="SleepTracker (Beautyrest) mattress sensor advertisements",
    version="1.0.0",
    core=False,
)
class SleepTrackerParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        if raw.company_id != SLEEPTRACKER_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload:
            return None

        id_hash = hashlib.sha256(
            f"sleeptracker:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
        }

        # Parse payload fields
        # [version/status][device_state][device_id x4][firmware x2]
        if len(payload) >= 2:
            metadata["device_state"] = payload[1]

        if len(payload) >= 6:
            metadata["device_id"] = payload[2:6].hex()

        if len(payload) >= 8:
            metadata["firmware_info"] = payload[6:8].hex()

        return ParseResult(
            parser_name="sleeptracker",
            beacon_type="sleeptracker",
            device_class="health",
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
                ("sleeptracker", limit),
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
            tab_name="SleepTracker",
            tab_icon="moon",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent SleepTracker Sightings",
                    data_endpoint="/api/sleeptracker/recent",
                    render_hints={"columns": ["timestamp", "local_name", "device_state", "device_id", "firmware_info", "rssi_max", "sighting_count"]},
                ),
            ],
        )
