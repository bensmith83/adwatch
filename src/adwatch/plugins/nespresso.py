"""Nespresso coffee machine BLE advertisement parser.

Per apk-ble-hunting/reports/nespresso-activities_passive.md. Two distinct
service UUIDs:

  - ``06AA1910-F22A-11E3-9DAA-0002A5D5C51B`` — coffee machines (Prodigio,
    Expert, Vertuo Plus/Next, Atelier, Pop, etc.)
  - ``65241910-0253-11E7-93AE-92361F002671`` — Aeroccino milk frother

The app filters scans by service UUID only — manufacturer data is not
parsed in the app's BLE scan path. CID ``0x2502`` is preserved for
backwards compatibility (legacy detection path); UUID-only matches are
the primary canonical signal per the report.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

NESPRESSO_COMPANY_ID = 0x2502
NESPRESSO_SERVICE_UUID = "06aa1910-f22a-11e3-9daa-0002a5d5c51b"
AEROCCINO_SERVICE_UUID = "65241910-0253-11e7-93ae-92361f002671"


@register_parser(
    name="nespresso",
    company_id=NESPRESSO_COMPANY_ID,
    service_uuid=[NESPRESSO_SERVICE_UUID, AEROCCINO_SERVICE_UUID],
    description="Nespresso machine + Aeroccino frother advertisements",
    version="1.1.0",
    core=False,
)
class NespressoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        machine_uuid_hit = NESPRESSO_SERVICE_UUID in normalized
        aeroccino_uuid_hit = AEROCCINO_SERVICE_UUID in normalized
        cid_hit = raw.company_id == NESPRESSO_COMPANY_ID

        if not (machine_uuid_hit or aeroccino_uuid_hit or cid_hit):
            return None

        metadata: dict = {}
        if aeroccino_uuid_hit:
            metadata["product_class"] = "aeroccino"
        elif machine_uuid_hit:
            metadata["product_class"] = "coffee_machine"
        elif cid_hit:
            metadata["product_class"] = "coffee_machine"

        payload = raw.manufacturer_payload
        if cid_hit and payload:
            metadata["payload_hex"] = payload.hex()
            metadata["payload_length"] = len(payload)
            if len(payload) >= 1:
                metadata["state_byte"] = payload[0]

        # Extract model info from local name (machine path only).
        # Patterns: Vertuo_CV6_FCB46765786E, Venus_D8132A9D825A
        if raw.local_name:
            parts = raw.local_name.split("_")
            if parts:
                metadata["model"] = parts[0]
                if len(parts) >= 3:
                    metadata["model_code"] = parts[1]
                    metadata["device_mac"] = parts[-1]
                elif len(parts) == 2:
                    metadata["device_mac"] = parts[-1]

        id_hash = hashlib.sha256(
            f"nespresso:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="nespresso",
            beacon_type="nespresso",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=(payload.hex() if payload else ""),
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
                ("nespresso", limit),
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
            tab_name="Nespresso",
            tab_icon="coffee",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Nespresso Sightings",
                    data_endpoint="/api/nespresso/recent",
                    render_hints={"columns": ["timestamp", "local_name", "model", "model_code", "state_byte", "rssi_max", "sighting_count"]},
                ),
            ],
        )
