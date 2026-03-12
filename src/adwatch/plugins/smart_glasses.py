"""Smart Glasses BLE advertisement parser.

Detects BLE advertisements from smart glasses manufacturers based on
company IDs assigned by the Bluetooth SIG. Based on research from
https://github.com/yjeanrenaud/yj_nearbyglasses

Known company IDs:
  0x01AB - Meta Platforms, Inc.
  0x058E - Meta Platforms Technologies, LLC
  0x0D53 - Luxottica Group S.p.A (Meta Ray-Ban manufacturer)
  0x03C2 - Snapchat, Inc. (Snap Spectacles)
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

SMART_GLASSES_COMPANY_IDS = [0x01AB, 0x058E, 0x0D53, 0x03C2]

MANUFACTURER_NAMES = {
    0x01AB: "Meta Platforms",
    0x058E: "Meta Platforms Technologies",
    0x0D53: "Luxottica",
    0x03C2: "Snapchat",
}


@register_parser(
    name="smart_glasses",
    company_id=SMART_GLASSES_COMPANY_IDS,
    description="Smart glasses BLE advertisements (Meta Ray-Ban, Snap Spectacles)",
    version="1.0.0",
    core=False,
)
class SmartGlassesParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 3:
            return None

        company_id = raw.company_id
        if company_id not in SMART_GLASSES_COMPANY_IDS:
            return None

        payload = raw.manufacturer_payload
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{payload.hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="smart_glasses",
            beacon_type="smart_glasses",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "manufacturer": MANUFACTURER_NAMES.get(company_id, "Unknown"),
                "company_id": f"0x{company_id:04x}",
                "payload_hex": payload.hex(),
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
                ("smart_glasses", limit),
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
            tab_name="Smart Glasses",
            tab_icon="glasses",
            widgets=[
                WidgetConfig(
                    widget_type="info_banner",
                    title="Detection Note",
                    data_endpoint="",
                    config={
                        "text": "Detection is based on Bluetooth SIG company IDs shared across all products from each manufacturer. "
                        "Matches may include other devices such as VR headsets, earbuds, or phones — not just smart glasses. "
                        "Manufacturers tracked: Meta Platforms (Ray-Ban Meta), Luxottica, Snapchat (Spectacles).",
                    },
                ),
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Smart Glasses Sightings",
                    data_endpoint="/api/smart_glasses/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "manufacturer", "company_id", "rssi_max", "sighting_count"]},
                ),
            ],
        )
