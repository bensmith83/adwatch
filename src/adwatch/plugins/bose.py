"""Bose audio device BLE advertisement parser.

Identifiers per apk-ble-hunting/reports/bose-bosemusic_passive.md.
"""

import hashlib
import re

from adwatch.models import (
    RawAdvertisement,
    ParseResult,
    PluginUIConfig,
    WidgetConfig,
    deserialize_service_data,
)
from adwatch.registry import register_parser


# Bluetooth SIG company ID for Bose Corporation.
BOSE_COMPANY_ID = 0x009E

# Primary SIG-assigned service UUID (Bose). Carries product-ID service data on
# some product lines.
BOSE_SERVICE_UUID_FEBE = "febe"

# Bose BMAP primary 128-bit service. Advertised by some BMAP-era products
# alongside (or instead of) the 16-bit FEBE.
BOSE_BMAP_SERVICE_UUID = "d417c028-9818-4354-99d1-2ac09d074591"

_BOSE_NAME_RE = re.compile(r"^Bose (.+)$")


@register_parser(
    name="bose",
    company_id=BOSE_COMPANY_ID,
    service_uuid=[BOSE_SERVICE_UUID_FEBE, BOSE_BMAP_SERVICE_UUID],
    local_name_pattern=_BOSE_NAME_RE.pattern,
    description="Bose audio device advertisements",
    version="1.1.0",
    core=False,
)
class BoseParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}
        matched = False

        if raw.manufacturer_data and raw.company_id == BOSE_COMPANY_ID:
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()
                metadata["payload_length"] = len(payload)
                matched = True

        if raw.service_data:
            for uuid in (BOSE_SERVICE_UUID_FEBE, BOSE_BMAP_SERVICE_UUID):
                svc = raw.service_data.get(uuid)
                if svc:
                    metadata["service_payload_hex"] = svc.hex()
                    metadata["service_payload_length"] = len(svc)
                    matched = True
                    break

        if raw.service_uuids:
            for uuid in raw.service_uuids:
                u = uuid.lower()
                if u == BOSE_SERVICE_UUID_FEBE or u == BOSE_BMAP_SERVICE_UUID:
                    matched = True
                    break

        name_match = _BOSE_NAME_RE.match(raw.local_name or "")
        if name_match:
            metadata["model_hint"] = name_match.group(1)
            matched = True

        if not matched:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]
        raw_hex = raw.manufacturer_payload.hex() if raw.manufacturer_payload else ""

        return ParseResult(
            parser_name="bose",
            beacon_type="bose",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
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
                ("bose", limit),
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
            tab_name="Bose",
            tab_icon="headphones",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Bose Sightings",
                    data_endpoint="/api/bose/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "model_hint", "payload_length", "rssi_max", "sighting_count"]},
                ),
            ],
        )
