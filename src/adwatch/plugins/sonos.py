"""Sonos speaker BLE advertisement parser.

Per apk-ble-hunting/reports/sonos-acr2_passive.md: discovery is by
SIG-assigned 16-bit service UUID ``0xFE07`` (Sonos, Inc.) — covers
speakers, soundbars, headphones, and portables. The companion app's only
``ScanFilter`` is on this UUID; CID ``0x05A7`` is Sonos's company ID and
appears in mfr-data on some product/firmware combinations.

Privacy note from the report: the advertised name is the user-set room
label (``Master Bedroom``, ``Kids Room``, ...). We surface it but
recommend downstream operators avoid uploading it.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

SONOS_COMPANY_ID = 0x05A7
SONOS_SERVICE_UUID = "fe07"

_NAME_RE = re.compile(r"^Sonos ")


@register_parser(
    name="sonos",
    company_id=SONOS_COMPANY_ID,
    service_uuid=SONOS_SERVICE_UUID,
    local_name_pattern=r"^Sonos ",
    description="Sonos speakers / soundbars / headphones",
    version="1.1.0",
    core=False,
)
class SonosParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == SONOS_COMPANY_ID
        # CID-only match requires a non-empty payload; otherwise it's just
        # an empty SIG-CID record with nothing to parse.
        payload_present = bool(raw.manufacturer_payload)
        cid_with_payload = cid_hit and payload_present

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = (
            SONOS_SERVICE_UUID in normalized
            or any(u.endswith("0000fe07-0000-1000-8000-00805f9b34fb") for u in normalized)
        )
        local_name = raw.local_name or ""
        name_hit = bool(_NAME_RE.match(local_name))

        if not (cid_with_payload or uuid_hit or name_hit):
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {}
        data = raw.manufacturer_payload or b""
        if cid_hit and data:
            metadata["payload_hex"] = data.hex()
            metadata["payload_length"] = len(data)
        if uuid_hit and "payload_length" not in metadata:
            metadata["match_source"] = "service_uuid"
            metadata["payload_length"] = 0
        if name_hit:
            metadata["device_name"] = local_name

        return ParseResult(
            parser_name="sonos",
            beacon_type="sonos",
            device_class="speaker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex() if data else "",
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
                ("sonos", limit),
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
            tab_name="Sonos",
            tab_icon="speaker",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Sonos Sightings",
                    data_endpoint="/api/sonos/recent",
                    render_hints={
                        "columns": ["timestamp", "mac_address", "local_name", "payload_length", "rssi_max", "sighting_count"],
                    },
                ),
            ],
        )
