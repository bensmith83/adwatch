"""Wyze Watch smartwatch BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

WYZE_COMPANY_ID = 0x0649
WYZE_NAME_PATTERN = re.compile(r"^Wyze Watch (\d+)")


@register_parser(
    name="wyze_watch",
    company_id=WYZE_COMPANY_ID,
    local_name_pattern=r"^Wyze Watch",
    description="Wyze Watch smartwatch advertisements",
    version="1.0.0",
    core=False,
)
class WyzeWatchParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Match by local name OR company ID
        name_match = raw.local_name and WYZE_NAME_PATTERN.match(raw.local_name)
        has_company = raw.manufacturer_data and len(raw.manufacturer_data) >= 4 and raw.company_id == WYZE_COMPANY_ID

        if not name_match and not has_company:
            return None

        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        payload = raw.manufacturer_payload
        if not payload:
            return None

        id_hash = hashlib.sha256(
            f"wyze_watch:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
        }

        # Device type from bytes 0-1 of payload
        if len(payload) >= 2:
            metadata["device_type"] = payload[0:2].hex()

        # Embedded MAC from bytes 4-9 of payload
        if len(payload) >= 10:
            mac_bytes = payload[4:10]
            metadata["embedded_mac"] = ":".join(f"{b:02X}" for b in mac_bytes)

        # Watch size from local name
        if name_match:
            metadata["watch_size"] = name_match.group(1)

        # MiBeacon data from FE95 service data
        if raw.service_data and "fe95" in raw.service_data:
            fe95_data = raw.service_data["fe95"]
            if fe95_data and len(fe95_data) >= 4:
                metadata["mibeacon_type"] = fe95_data[2:4].hex()

        return ParseResult(
            parser_name="wyze_watch",
            beacon_type="wyze_watch",
            device_class="wearable",
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
                ("wyze_watch", limit),
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
            tab_name="Wyze Watch",
            tab_icon="watch",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Wyze Watch Sightings",
                    data_endpoint="/api/wyze_watch/recent",
                    render_hints={"columns": ["timestamp", "local_name", "watch_size", "embedded_mac", "rssi_max", "sighting_count"]},
                ),
            ],
        )
