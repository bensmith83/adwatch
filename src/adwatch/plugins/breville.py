"""Breville / ChefSteps Joule appliance plugin.

Per apk-ble-hunting/reports/breville-connectedcoffee_passive.md and
chefsteps-circulator_passive.md. Two distinct Breville-ecosystem
advertisement shapes:

1. **Modern Breville** (CID ``0x0955`` = 2389) — version + model byte +
   4-byte unique appliance ID. Covers Oracle Jet, Oracle Touch, Barista
   Touch Impress, Smart Oven Air Fryer Pro, BSV600 / BEA900 SKUs, plus the
   LUNAR scale (model byte 0xFE).

2. **Legacy ChefSteps Joule** (CID ``0x0159`` = 345, Breville Pty Ltd) —
   protocol type byte + 5-byte family prefix ``A0 A3 5D B7 E1`` + 3-byte
   per-device variant. Joule also advertises the 128-bit service UUID
   ``700B4321-9836-4383-A2B2-31A9098D1473``.

Acaia LUNAR's separate ``0x4242`` ASCII-"BB" sentinel CID is handled by
``acaia_scale`` (enriched there, not here).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


BREVILLE_MODERN_CID = 0x0955  # 2389
BREVILLE_LEGACY_CID = 0x0159  # 345 (Breville Pty Ltd)
JOULE_SERVICE_UUID = "700b4321-9836-4383-a2b2-31a9098d1473"

# From BleDevice.java in com.breville.connectedcoffee.
MODERN_MODEL_TABLE = {
    0x00: "CSJ100",
    0x01: "BOV950",
    0x02: "BSV600",
    0x03: "BES995",
    0x04: "BES1010",
    0x05: "BEA900",
    0x06: "BES87x",
    0xFE: "LUNAR",
}

# Joule legacy "family-prefix" — the 5 bytes immediately after the type byte.
_JOULE_FAMILY_PREFIX = bytes.fromhex("a0a35db7e1")


@register_parser(
    name="breville",
    company_id=[BREVILLE_MODERN_CID, BREVILLE_LEGACY_CID],
    service_uuid=JOULE_SERVICE_UUID,
    description="Breville appliances + ChefSteps Joule",
    version="1.0.0",
    core=False,
)
class BrevilleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid = raw.company_id
        payload = raw.manufacturer_payload or b""

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        joule_uuid_hit = JOULE_SERVICE_UUID in normalized

        if cid == BREVILLE_MODERN_CID:
            return self._parse_modern(raw, payload)
        if cid == BREVILLE_LEGACY_CID or joule_uuid_hit:
            return self._parse_legacy(raw, payload, uuid_only=joule_uuid_hit and cid != BREVILLE_LEGACY_CID)

        return None

    def _parse_modern(self, raw: RawAdvertisement, payload: bytes) -> ParseResult:
        metadata: dict = {"vendor": "Breville", "family": "modern"}

        if len(payload) >= 1:
            metadata["protocol_version"] = payload[0]
        unique_hex: str | None = None
        if len(payload) >= 2:
            model_byte = payload[1]
            metadata["model_byte"] = model_byte
            metadata["model"] = MODERN_MODEL_TABLE.get(
                model_byte, f"unknown_0x{model_byte:02X}"
            )
        if len(payload) >= 7:
            unique_hex = payload[3:7].hex().upper()
            metadata["unique_id"] = unique_hex

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if unique_hex is not None:
            id_basis = f"breville:{unique_hex}"
        else:
            id_basis = f"breville:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="breville",
            beacon_type="breville",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def _parse_legacy(self, raw: RawAdvertisement, payload: bytes, *, uuid_only: bool) -> ParseResult:
        metadata: dict = {
            "vendor": "Breville",
            "family": "joule_legacy",
            "model": "Joule",
        }

        variant: str | None = None
        if not uuid_only and len(payload) >= 1:
            metadata["type_byte"] = payload[0]

        if not uuid_only and len(payload) >= 9 and payload[1:6] == _JOULE_FAMILY_PREFIX:
            variant = payload[6:9].hex()
            metadata["device_variant"] = variant
            metadata["family_prefix_match"] = True

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if variant is not None:
            id_basis = f"breville_joule:{variant}"
        else:
            id_basis = f"breville_joule:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="breville",
            beacon_type="breville",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
