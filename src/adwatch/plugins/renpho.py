"""Renpho / Qingniu smart scale plugin.

Per apk-ble-hunting/reports/qingniu-renpho_passive.md: Qingniu's OEM
firmware powers many sub-brand scales (Renpho, Yolanda, JiaHua, Dretec,
Wbird, Sunnyway, JiaBao, Beryl). The brand is encoded in the BLE
local-name prefix; the canonical CID is Qingniu's SIG-assigned
``0x0157``. Some hardware also exposes a live weight preview in
manufacturer-data (kg/lb selector + stable bit + LE16 weight in 100g
units). The legacy Renpho-branded SIG CID ``0x06D0`` is also kept for
backwards compatibility with existing installs.

Service UUIDs vary by hardware vintage: ``0xFFF0``, ``0xFFE0``,
``0xABF0``, and SIG WSP ``0x181D`` are all observed.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# CIDs:
#   0x06D0 — Renpho-branded SIG registration (legacy)
#   0x0157 — Qingniu Inc. SIG registration (canonical OEM)
RENPHO_COMPANY_ID = 0x06D0
QINGNIU_COMPANY_ID = 0x0157

# Service UUIDs across hardware vintages.
QINGNIU_SERVICE_UUIDS = ["fff0", "ffe0", "abf0", "181d"]

# From oo0oOO0/renpho0Orenphorenphoo.java:19. The CR-terminated
# QN-WristBand variant is intentional in the source.
_NAME_CATALOG = (
    "QN-Scale",
    "Yolanda-CS20H", "Yolanda-CS20I", "Yolanda-CS10",
    "Yolanda-CS10C", "Yolanda-CS20A", "Yolanda-CS30A",
    "Yolanda-CS20E", "Yolanda-CS20F", "Yolanda-CS20G",
    "CS30C", "JiaHua-CS50A", "Dretec-CS50A", "Wbird-CS50A",
    "Yolanda-CS20B", "Sunnyway-CS50A", "JiaBao-CS50A",
    "Beryl-CS50A", "QN-WristBand",
    "Yolanda-CS10C1", "Yolanda-CS11", "Yolanda-CS20E1",
    "Yolanda-CS20E2", "Yolanda-CS20F1", "Yolanda-CS20F2",
    "Yolanda-CS20G1", "Yolanda-CS20G2", "Beryl-CS40A",
    "QN-Scale1",
)

# Anchored regex covering the catalog above. Order doesn't matter for
# disjunction; we sort longest-first to make sub-brand prefixes win
# over their parents (e.g. ``QN-Scale1`` over ``QN-Scale``).
_NAME_PATTERN = (
    r"^(" + "|".join(re.escape(n) for n in sorted(_NAME_CATALOG, key=len, reverse=True)) + r")"
)
_NAME_RE = re.compile(_NAME_PATTERN)

_BRAND_FROM_PREFIX = {
    "QN-": "Qingniu",
    "Yolanda-": "Yolanda",
    "JiaHua-": "JiaHua",
    "Dretec-": "Dretec",
    "Wbird-": "Wbird",
    "Sunnyway-": "Sunnyway",
    "JiaBao-": "JiaBao",
    "Beryl-": "Beryl",
    "CS30C": "Yolanda",
}


@register_parser(
    name="renpho",
    company_id=[RENPHO_COMPANY_ID, QINGNIU_COMPANY_ID],
    service_uuid=QINGNIU_SERVICE_UUIDS,
    local_name_pattern=_NAME_PATTERN,
    description="Renpho / Qingniu OEM scales (Yolanda/Dretec/Wbird/JiaHua/etc.)",
    version="2.0.0",
    core=False,
)
class RenphoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""
        cid = raw.company_id
        cid_hit = cid in (RENPHO_COMPANY_ID, QINGNIU_COMPANY_ID)

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = False
        for short in QINGNIU_SERVICE_UUIDS:
            full = f"0000{short}-0000-1000-8000-00805f9b34fb"
            if short in normalized or full in normalized:
                uuid_hit = True
                break

        name_match = _NAME_RE.match(local_name)
        if not (cid_hit or uuid_hit or name_match):
            return None

        metadata: dict = {}
        if name_match:
            matched = name_match.group(1)
            metadata["name_prefix"] = matched
            metadata["device_name"] = local_name
            for prefix, brand in _BRAND_FROM_PREFIX.items():
                if matched.startswith(prefix):
                    metadata["brand"] = brand
                    break
            else:
                metadata["brand"] = "Qingniu"
            # Strip the brand- to expose the model code (CS20E, CS30A, ...).
            for prefix in _BRAND_FROM_PREFIX:
                if matched.startswith(prefix) and prefix.endswith("-"):
                    metadata["model_code"] = matched[len(prefix):]
                    break

        if cid == QINGNIU_COMPANY_ID:
            metadata["qingniu_cid"] = True
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 3:
                weight_raw = int.from_bytes(payload[0:2], "little")
                metadata["weight_kg"] = round(weight_raw / 10.0, 2)
                flags = payload[2]
                unit_bits = flags & 0x0F
                unit_map = {0: "kg", 1: "lb", 2: "jin"}
                metadata["unit"] = unit_map.get(unit_bits, f"raw_{unit_bits}")
                metadata["stable"] = bool(flags & 0x10)
                if len(payload) >= 10:
                    mac_tail = payload[4:10]
                    metadata["embedded_mac"] = ":".join(f"{b:02X}" for b in reversed(mac_tail))

        if cid == RENPHO_COMPANY_ID:
            metadata["renpho_cid"] = True

        # Identity preference: embedded MAC tail (when present) > model+mac > mac+name
        if metadata.get("embedded_mac"):
            id_basis = f"renpho:{metadata['embedded_mac']}"
        elif local_name:
            id_basis = f"{raw.mac_address}:{local_name}"
        else:
            id_basis = f"{raw.mac_address}:renpho"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        payload = raw.manufacturer_payload
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="renpho",
            beacon_type="renpho",
            device_class="scale",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
