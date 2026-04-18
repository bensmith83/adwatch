"""Orbit B-hyve smart irrigation BLE advertisement parser.

Per apk-ble-hunting/reports/orbit-smarthome_passive.md. Name pattern
`bhyve_<6hex>` plus vendor UUIDs in the `fe32-4f58-8b78-98e42b2c047f` base.
State lives behind GATT, not in the advertisement.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


_BHYVE_NAME_RE = re.compile(r"^bhyve_([0-9a-f]{6})$")

# Observed vendor UUID base; concrete UUIDs per service not fully enumerated
# in the passive report, so we match the base pattern.
_BHYVE_BASE_RE = re.compile(
    r"^[0-9a-f]{8}-fe32-4f58-8b78-98e42b2c047f$"
)


@register_parser(
    name="orbit_bhyve",
    local_name_pattern=_BHYVE_NAME_RE.pattern,
    description="Orbit B-hyve smart irrigation controllers / valves",
    version="1.0.0",
    core=False,
)
class OrbitBhyveParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        m = _BHYVE_NAME_RE.match(name)

        vendor_uuid = None
        for u in (raw.service_uuids or []):
            if _BHYVE_BASE_RE.match(u.lower()):
                vendor_uuid = u.lower()
                break

        if not m and not vendor_uuid:
            return None

        metadata: dict = {}
        device_id_suffix = None
        if m:
            device_id_suffix = m.group(1)
            metadata["device_name"] = name
            metadata["device_id_suffix"] = device_id_suffix
        if vendor_uuid:
            metadata["vendor_uuid"] = vendor_uuid

        if device_id_suffix:
            id_basis = f"orbit_bhyve:{device_id_suffix}"
        else:
            id_basis = f"orbit_bhyve:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="orbit_bhyve",
            beacon_type="orbit_bhyve",
            device_class="irrigation",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
