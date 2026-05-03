"""WHOOP fitness strap plugin.

Per apk-ble-hunting/reports/whoop-android_passive.md:

  Three generation-specific 128-bit service UUIDs:
    - 61080001-... — Gen4 (Harvard)
    - fd4b0001-... — 4.0 Maverick / Goose
    - 11500001-... — Puffin (5.x / 2023+)

  Local name: ^WHOOP[ _-]<hex serial>. No mfr-data, no service-data.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WHOOP_GEN4_UUID = "61080001-8d6d-82b8-614a-1c8cb0f8dcc6"
WHOOP_MAVERICK_UUID = "fd4b0001-cce1-4033-93ce-002d5875f58a"
WHOOP_PUFFIN_UUID = "11500001-6215-11ee-8c99-0242ac120002"

GENERATION_NAMES = {
    WHOOP_GEN4_UUID: "Gen4",
    WHOOP_MAVERICK_UUID: "Maverick",
    WHOOP_PUFFIN_UUID: "Puffin",
}

_NAME_RE = re.compile(r"^WHOOP[ _-]?([A-Fa-f0-9]+)$")


@register_parser(
    name="whoop",
    service_uuid=(WHOOP_GEN4_UUID, WHOOP_MAVERICK_UUID, WHOOP_PUFFIN_UUID),
    local_name_pattern=r"^WHOOP",
    description="WHOOP fitness strap (Gen4 / 4.0 Maverick / 5.x Puffin)",
    version="1.0.0",
    core=False,
)
class WhoopParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        matched_uuids = [u for u in normalized if u in GENERATION_NAMES]
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None
        name_loose = bool(raw.local_name and raw.local_name.startswith("WHOOP"))

        if not (matched_uuids or name_loose):
            return None

        metadata: dict = {}

        if matched_uuids:
            uuid = matched_uuids[0]
            metadata["generation"] = GENERATION_NAMES[uuid]
            metadata["generation_uuid"] = uuid

        if name_match:
            metadata["serial"] = name_match.group(1).upper()
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Identity prefers the in-name serial when available.
        if name_match:
            id_basis = f"whoop:{name_match.group(1).upper()}"
        else:
            id_basis = f"whoop:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="whoop",
            beacon_type="whoop",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
