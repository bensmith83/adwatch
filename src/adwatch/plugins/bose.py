"""Bose audio device BLE advertisement parser.

Identifiers per apk-ble-hunting/reports/bose-bosemusic_passive.md and
apk-ble-hunting/reports/bose-monet_passive.md.
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

# SIG-assigned service UUIDs.
BOSE_SERVICE_UUID_FEBE = "febe"  # primary
BOSE_SERVICE_UUID_FDD2 = "fdd2"  # secondary (Bose Monet path)

# Bose BMAP primary 128-bit service.
BOSE_BMAP_SERVICE_UUID = "d417c028-9818-4354-99d1-2ac09d074591"
# Additional Bose 128-bit vendor UUID (Monet path).
BOSE_VENDOR_UUID = "f4c93a79-d04f-4565-b05e-79f7ead9df8e"

# Mfr-data variant byte → parser family name.
VARIANT_PARSERS = {
    0x9E: "120-series",
    0x03: "104-series",
    0x10: "legacy",
    0x00: "legacy",
    0x01: "legacy",
    0x41: "bragi",
}

_BOSE_NAME_RE = re.compile(r"^Bose (.+)$")


@register_parser(
    name="bose",
    company_id=BOSE_COMPANY_ID,
    service_uuid=[
        BOSE_SERVICE_UUID_FEBE,
        BOSE_SERVICE_UUID_FDD2,
        BOSE_BMAP_SERVICE_UUID,
        BOSE_VENDOR_UUID,
    ],
    local_name_pattern=_BOSE_NAME_RE.pattern,
    description="Bose audio device advertisements",
    version="1.2.0",
    core=False,
)
class BoseParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}
        matched = False

        mac_hash_hex = None

        if raw.manufacturer_data and raw.company_id == BOSE_COMPANY_ID:
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()
                metadata["payload_length"] = len(payload)
                matched = True
                # Variant discriminator (per Bose Monet report).
                if len(payload) >= 1:
                    variant_byte = payload[0]
                    metadata["variant_byte"] = variant_byte
                    metadata["variant_family"] = VARIANT_PARSERS.get(
                        variant_byte, f"unknown_{variant_byte:02x}"
                    )
                # 5-byte partial MAC hash at offsets 4-8 — stable per device,
                # used as identity basis to survive BLE address rotation.
                if len(payload) >= 9:
                    mac_hash_hex = payload[4:9].hex()
                    metadata["mac_hash_5b_hex"] = mac_hash_hex

        if raw.service_data:
            for uuid in (BOSE_SERVICE_UUID_FEBE, BOSE_SERVICE_UUID_FDD2,
                         BOSE_BMAP_SERVICE_UUID, BOSE_VENDOR_UUID):
                svc = raw.service_data.get(uuid)
                if svc:
                    metadata["service_payload_hex"] = svc.hex()
                    metadata["service_payload_length"] = len(svc)
                    matched = True
                    break

        if raw.service_uuids:
            for uuid in raw.service_uuids:
                u = uuid.lower()
                if u in (BOSE_SERVICE_UUID_FEBE, BOSE_SERVICE_UUID_FDD2,
                         BOSE_BMAP_SERVICE_UUID, BOSE_VENDOR_UUID):
                    matched = True
                    break

        name_match = _BOSE_NAME_RE.match(raw.local_name or "")
        if name_match:
            metadata["model_hint"] = name_match.group(1)
            matched = True

        if not matched:
            return None

        # Identity prefers the in-payload MAC hash (stable across BLE address
        # rotation) per the Monet passive report.
        if mac_hash_hex:
            id_basis = f"bose:{mac_hash_hex}"
        else:
            id_basis = raw.mac_address
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]
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
