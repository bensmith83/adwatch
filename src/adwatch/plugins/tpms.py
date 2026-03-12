"""TPMS (Tire Pressure Monitoring System) BLE advertisement parser."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser


@register_parser(
    name="tpms",
    company_id=0x0001,
    local_name_pattern=r"^(TPMS|BR)",
    description="BLE tire pressure monitoring sensors",
    version="1.0.0",
    core=False,
)
class TPMSParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 5:
            return None

        try:
            return self._parse_inner(raw, payload)
        except struct.error:
            return None

    def _parse_inner(self, raw: RawAdvertisement, payload: bytes) -> ParseResult | None:
        sensor_index = payload[0]
        battery_voltage = payload[1] * 0.02
        temperature_c = payload[2] - 40
        pressure_kpa = struct.unpack_from("<H", payload, 3)[0] / 100.0

        id_hash = hashlib.sha256(
            f"{raw.mac_address}{sensor_index}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tpms",
            beacon_type="tpms",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "sensor_index": sensor_index,
                "battery_voltage": battery_voltage,
                "temperature_c": temperature_c,
                "pressure_kpa": pressure_kpa,
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
                ("tpms", limit),
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
            tab_name="TPMS",
            tab_icon="gauge",
            widgets=[
                WidgetConfig(
                    widget_type="sensor_card",
                    title="Tire Pressure Sensors",
                    data_endpoint="/api/tpms/recent",
                    config={
                        "fields": ["sensor_index", "pressure_kpa", "temperature_c", "battery_voltage"],
                    },
                    render_hints={
                        "primary_field": "pressure_kpa",
                        "secondary_field": "temperature_c",
                        "badge_fields": ["sensor_index"],
                        "unit": "pressure",
                    },
                ),
            ],
            refresh_interval=10,
        )
