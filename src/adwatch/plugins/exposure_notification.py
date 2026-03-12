"""Exposure Notification (GAEN / COVID-19) BLE advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

SERVICE_UUID = "0000fd6f-0000-1000-8000-00805f9b34fb"
EXPECTED_LEN = 20  # 16-byte RPI + 4-byte AEM


@register_parser(
    name="exposure_notification",
    service_uuid=SERVICE_UUID,
    description="Exposure Notification (GAEN)",
    version="1.0.0",
    core=False,
)
class ExposureNotificationParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or SERVICE_UUID not in raw.service_data:
            return None

        data = raw.service_data[SERVICE_UUID]
        if not data or len(data) < EXPECTED_LEN:
            return None

        rpi = data[:16]
        aem = data[16:20]
        tx_power = struct.unpack("b", bytes([aem[1]]))[0]

        id_hash = hashlib.sha256(rpi.hex().encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="exposure_notification",
            beacon_type="exposure_notification",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "rpi_hex": rpi.hex(),
                "aem_hex": aem.hex(),
                "tx_power": tx_power,
            },
        )

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
                ("exposure_notification", limit),
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
            tab_name="Exposure Notification",
            tab_icon="shield",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent EN Sightings",
                    data_endpoint="/api/exposure_notification/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "tx_power", "rpi_hex", "rssi_max", "sighting_count"]},
                ),
            ],
        )
