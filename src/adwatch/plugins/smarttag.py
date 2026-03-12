"""Samsung SmartTag BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

import struct

SMARTTAG_UUID = "fd5a"

_LOST_MODES = {0: "normal", 1: "near_owner", 2: "lost", 3: "overmature_lost"}


@register_parser(
    name="smarttag",
    service_uuid=SMARTTAG_UUID,
    description="Samsung SmartTag tracker advertisements",
    version="1.0.0",
    core=False,
)
class SmartTagParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or SMARTTAG_UUID not in raw.service_data:
            return None

        data = raw.service_data[SMARTTAG_UUID]
        if not data:
            return None

        metadata = {"payload_hex": data.hex()}

        if len(data) == 20:
            privacy_id = data[0:8].hex()
            aging_counter = struct.unpack(">H", data[8:10])[0]
            signature = data[10:18].hex()
            state = data[18]
            lost_mode = _LOST_MODES[(state >> 6) & 0x03]
            uwb_available = bool((state >> 5) & 0x01)
            battery_level = state & 0x1F

            metadata.update({
                "privacy_id": privacy_id,
                "aging_counter": aging_counter,
                "signature": signature,
                "lost_mode": lost_mode,
                "uwb_available": uwb_available,
                "battery_level": battery_level,
            })
            id_input = f"{raw.mac_address}:{privacy_id}"
        else:
            id_input = f"{raw.mac_address}:{data.hex()}"

        id_hash = hashlib.sha256(id_input.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="smarttag",
            beacon_type="smarttag",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
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
                ("smarttag", limit),
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
            tab_name="SmartTag",
            tab_icon="radio",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent SmartTag Sightings",
                    data_endpoint="/api/smarttag/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "lost_mode", "battery_level", "uwb_available", "rssi_max", "sighting_count"]},
                ),
            ],
        )
