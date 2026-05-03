"""Hatch baby sound machine / night light BLE advertisement parser.

Service UUIDs added per apk-ble-hunting/reports/hatchbaby-rest_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser


# Vendor 128-bit service UUIDs per the passive report.
HATCH_GEN1_SERVICE_UUID = "02240000-5efd-47eb-9c1a-de53f7a2b232"
HATCH_GEN2_SERVICE_UUID = "02260000-5efd-47eb-9c1a-de53f7a2b232"
NORDIC_LEGACY_DFU_UUID = "00001530-1212-efde-1523-785feabcd123"


@register_parser(
    name="hatch",
    company_id=0x0434,
    service_uuid=(HATCH_GEN1_SERVICE_UUID, HATCH_GEN2_SERVICE_UUID),
    local_name_pattern=r"^Hatch ",
    description="Hatch Rest/Restore baby sound machines and night lights",
    version="1.1.0",
    core=False,
)
class HatchParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # The parser used to require manufacturer_data with CID 0x0434, but per
        # the passive report Hatch devices may advertise via vendor service UUID
        # alone. Accept either signal.
        normalized_uuids = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = any(
            u == HATCH_GEN1_SERVICE_UUID or u == HATCH_GEN2_SERVICE_UUID
            for u in normalized_uuids
        )
        cid_hit = raw.company_id == 0x0434
        name_hit = bool(raw.local_name and raw.local_name.startswith("Hatch "))

        if not (uuid_hit or cid_hit or name_hit):
            return None

        # CID-only match with no payload is not useful — preserve legacy guard.
        if cid_hit and not uuid_hit and not name_hit and not raw.manufacturer_payload:
            return None

        payload = raw.manufacturer_payload or b""

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict[str, str | int | float | bool] = {
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
        }

        # Generation tag from vendor service UUID.
        if HATCH_GEN1_SERVICE_UUID in normalized_uuids:
            metadata["generation"] = "gen1"
        elif HATCH_GEN2_SERVICE_UUID in normalized_uuids:
            metadata["generation"] = "gen2"

        if NORDIC_LEGACY_DFU_UUID in normalized_uuids:
            metadata["dfu_mode"] = True

        # Battery level from standard Battery Service (UUID 180f)
        if raw.service_data and "180f" in raw.service_data:
            battery_bytes = raw.service_data["180f"]
            if battery_bytes:
                metadata["battery_level"] = battery_bytes[0]

        # Device name from local_name
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Build stable key excluding rolling counter (byte 5 of payload)
        stable = bytearray(payload)
        if len(stable) > 5:
            stable[5] = 0
        stable_key = f"hatch|{bytes(stable).hex()}|{raw.local_name or ''}"

        return ParseResult(
            parser_name="hatch",
            beacon_type="hatch",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
            stable_key=stable_key,
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
                ("hatch", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                mfr_hex = item.get("manufacturer_data_hex")
                if mfr_hex:
                    try:
                        svc_data = None
                        svc_json = item.get("service_data_json")
                        if svc_json:
                            svc_data = deserialize_service_data(svc_json)
                        raw = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=bytes.fromhex(mfr_hex),
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
            tab_name="Hatch",
            tab_icon="baby",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Hatch Devices",
                    data_endpoint="/api/hatch/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "battery_level", "rssi_max", "sighting_count"]},
                ),
            ],
        )
