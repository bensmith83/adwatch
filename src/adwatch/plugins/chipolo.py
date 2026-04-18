"""Chipolo tracker tag plugin.

Identifiers and variants per apk-ble-hunting/reports/chipolo-net-v3_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


CHIPOLO_COMPANY_ID = 0x08C3

# Service UUIDs used by the Chipolo app scan filters.
SERVICE_UUID_LEGACY = "fe33"     # legacy Chipolo tags (presence-only)
SERVICE_UUID_CURRENT = "fe65"    # current Chipolo tags
SERVICE_UUID_FMDN = "fd44"       # Google Fast Pair / Find My Device Network

# iBeacon proximity UUID embedded under Apple company ID (0x004C) for
# Chipolo-in-iBeacon-mode. Published here as a constant so the iBeacon parser
# (or a downstream enricher) can tag proximity-UUID hits as Chipolo; this
# plugin does not register for 0x004C directly to avoid colliding with the
# Apple continuity parsers.
CHIPOLO_PROXIMITY_UUID = "9ee14dfb-67f0-400f-86d1-4c2728b83f0f"

# 8-byte FMDN service-data prefixes from jx/a.java:25-26 (mask = all ones).
CHIPOLO_FMDN_PREFIX_A = bytes.fromhex("8dae5760d6b85941")
CHIPOLO_FMDN_PREFIX_B = bytes.fromhex("8dae5760e3451d04")

COLORS = {
    0: "Gray",
    1: "White",
    2: "Black",
    3: "Violet",
    4: "Blue",
    5: "Green",
    6: "Yellow",
    7: "Orange",
    8: "Red",
    9: "Pink",
}


@register_parser(
    name="chipolo",
    company_id=CHIPOLO_COMPANY_ID,
    service_uuid=[SERVICE_UUID_LEGACY, SERVICE_UUID_CURRENT, SERVICE_UUID_FMDN],
    description="Chipolo tracker tags",
    version="1.1.0",
    core=False,
)
class ChipoloParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}
        variant = None

        sd = raw.service_data or {}
        if SERVICE_UUID_LEGACY in sd:
            svc = sd[SERVICE_UUID_LEGACY]
            variant = "legacy"
            if svc and len(svc) >= 1:
                color_code = svc[0]
                metadata["color_code"] = color_code
                metadata["color"] = COLORS.get(color_code, "Unknown")
        elif SERVICE_UUID_CURRENT in sd:
            variant = "current"
        elif SERVICE_UUID_FMDN in sd:
            svc = sd[SERVICE_UUID_FMDN]
            if svc and svc.startswith(CHIPOLO_FMDN_PREFIX_A):
                variant = "fmdn_a"
                metadata["fmdn_rotating_id_hex"] = svc[8:].hex()
            elif svc and svc.startswith(CHIPOLO_FMDN_PREFIX_B):
                variant = "fmdn_b"
                metadata["fmdn_rotating_id_hex"] = svc[8:].hex()
            else:
                variant = "fmdn"

        if variant is not None:
            metadata["variant"] = variant

        payload = raw.manufacturer_payload
        raw_hex = payload.hex() if payload else ""

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:chipolo".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="chipolo",
            beacon_type="chipolo",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
