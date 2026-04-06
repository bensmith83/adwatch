"""Hunter Douglas PowerView Gen 3 motorized shade BLE advertisement parser.

PowerView Gen 3 shades (Silhouette, Duette, Vignette, etc.) advertise with
service UUID FDC1 (registered to Hunter Douglas) and company ID 0x0819.
The manufacturer data contains real-time shade state: position, tilt, battery.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

HUNTER_DOUGLAS_COMPANY_ID = 0x0819
HUNTER_DOUGLAS_SERVICE_UUID = "fdc1"

# Known local name prefixes -> product lines
PRODUCT_PREFIXES = {
    "SIL": "Silhouette",
    "DUE": "Duette",
    "VIG": "Vignette",
    "SON": "Sonnette",
    "PRO": "Provenance",
    "PIR": "Pirouette",
}

NAME_RE = re.compile(r"^([A-Z]{3}):([0-9A-Fa-f]{4})$")

MOTION_FLAGS = {0: "idle", 1: "closing", 2: "opening", 3: "charging"}
BATTERY_LEVELS = {3: "100%", 2: "50%", 1: "20%", 0: "0%"}


def _decode_v2_payload(payload: bytes) -> dict:
    """Decode 9-byte V2 manufacturer data payload (after company ID)."""
    if len(payload) < 9:
        return {}

    home_id = int.from_bytes(payload[0:2], "little")
    type_id = payload[2]
    pos1_raw = int.from_bytes(payload[3:5], "little")
    position_pct = round((pos1_raw >> 2) / 10.0, 1)
    motion_flag = pos1_raw & 0x03
    tilt = payload[7]
    status = payload[8]
    battery_level = (status >> 6) & 0x03

    return {
        "home_id": f"0x{home_id:04x}",
        "type_id": type_id,
        "position_pct": position_pct,
        "motion": MOTION_FLAGS.get(motion_flag, f"unknown({motion_flag})"),
        "tilt": tilt,
        "battery": BATTERY_LEVELS.get(battery_level, f"unknown({battery_level})"),
    }


@register_parser(
    name="hunter_douglas_powerview",
    company_id=HUNTER_DOUGLAS_COMPANY_ID,
    service_uuid=HUNTER_DOUGLAS_SERVICE_UUID,
    local_name_pattern=r"^[A-Z]{3}:[0-9A-Fa-f]{4}$",
    description="Hunter Douglas PowerView Gen 3 motorized shade advertisements",
    version="1.0.0",
    core=False,
)
class HunterDouglasPowerViewParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        company_match = raw.company_id == HUNTER_DOUGLAS_COMPANY_ID
        uuid_match = any(HUNTER_DOUGLAS_SERVICE_UUID in u for u in raw.service_uuids)

        if not company_match and not uuid_match:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:hunter_douglas".encode()
        ).hexdigest()[:16]

        metadata: dict = {}

        if raw.local_name:
            m = NAME_RE.match(raw.local_name)
            if m:
                prefix = m.group(1)
                metadata["product_line"] = PRODUCT_PREFIXES.get(prefix, prefix)
                metadata["device_id"] = m.group(2)
                metadata["device_name"] = raw.local_name

        if raw.manufacturer_payload and len(raw.manufacturer_payload) >= 9:
            metadata.update(_decode_v2_payload(raw.manufacturer_payload))

        return ParseResult(
            parser_name="hunter_douglas_powerview",
            beacon_type="hunter_douglas",
            device_class="motorized_shade",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
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
                "SELECT *, last_seen AS timestamp FROM raw_advertisements "
                "WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("hunter_douglas_powerview", limit),
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
            tab_name="Shades",
            tab_icon="blinds",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Hunter Douglas PowerView Shades",
                    data_endpoint="/api/hunter_douglas_powerview/recent",
                    render_hints={
                        "columns": [
                            "timestamp",
                            "local_name",
                            "product_line",
                            "position_pct",
                            "tilt",
                            "battery",
                            "motion",
                            "home_id",
                            "rssi_max",
                            "sighting_count",
                        ]
                    },
                ),
            ],
        )
