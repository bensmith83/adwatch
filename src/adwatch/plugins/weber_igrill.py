"""Weber iGrill / Kitchen Thermometer / Pulse plugin.

Name prefixes, model mapping, and per-model service UUIDs per
apk-ble-hunting/reports/weber-igrill_passive.md.

Weber's BLE SIG company ID is 0x043F (1087, "Weber-Stephen Products").
Telemetry (probe temperatures, battery) requires GATT — advertisement
carries only model identification.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WEBER_COMPANY_ID = 0x043F

# Per-model 128-bit service UUIDs (from the Weber app prefix table).
WEBER_SERVICE_UUIDS = (
    "38e70000-de63-4b00-9d76-9b2e6e6c5a8f",  # Kitchen Thermometer Mini
    "19450000-de63-4b00-9d76-9b2e6e6c5a8f",  # Kitchen Thermometer
    "6e910000-de63-4b00-9d76-9b2e6e6c5a8f",  # iGrill_Mini v1
    "ada7590f-de63-4b00-9d76-9b2e6e6c5a8f",  # iGrill_Mini v2
    "9d610c43-de63-4b00-9d76-9b2e6e6c5a8f",  # iGrill_v2 / B2 model
    "6c910000-de63-4b00-9d76-9b2e6e6c5a8f",  # Pulse
)

# Longest-first per the Weber app's prefix dispatch.
_PREFIX_MODEL = [
    ("igrill_mini_2", "iGrill Mini v2"),
    ("igrill_mini02", "iGrill Mini v2"),
    ("igrill_mini", "iGrill Mini"),
    ("igrill_v2_2", "iGrill v2 (B2)"),
    ("igrill_v2", "iGrill v2"),
    ("igrill_v3", "iGrill v3"),
    ("igrill2", "iGrill 2"),
    ("igrill3", "iGrill 3"),
    ("kt_mini", "Kitchen Thermometer Mini"),
    ("kt", "Kitchen Thermometer"),
    ("pulse 2000", "Pulse 2000"),
    ("pulse 1000", "Pulse 1000"),
    # Generic fallback last
    ("igrill", "iGrill Unknown"),
]

# Heuristic probe-count by model family.
_PROBE_COUNTS = {
    "iGrill Mini": 1,
    "iGrill Mini v2": 1,
    "Kitchen Thermometer Mini": 1,
    "Kitchen Thermometer": 2,
    "iGrill 2": 4,
    "iGrill 3": 4,
    "iGrill v2": 4,
    "iGrill v2 (B2)": 4,
    "iGrill v3": 4,
    "Pulse 1000": 4,
    "Pulse 2000": 4,
}

_NAME_RE = re.compile(r"(?i)^(igrill|kt_|kt$|pulse \d+)")


@register_parser(
    name="weber_igrill",
    company_id=WEBER_COMPANY_ID,
    service_uuid=WEBER_SERVICE_UUIDS,
    local_name_pattern=r"(?i)^(igrill|kt_|kt$|pulse \d+)",
    description="Weber iGrill / Kitchen Thermometer / Pulse",
    version="1.1.0",
    core=False,
)
class WeberIGrillParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""
        name_lower = local_name.lower()
        name_hit = bool(_NAME_RE.match(local_name)) if local_name else False

        cid_hit = raw.company_id == WEBER_COMPANY_ID
        uuid_hit = any(u.lower() in WEBER_SERVICE_UUIDS for u in (raw.service_uuids or []))

        if not (name_hit or cid_hit or uuid_hit):
            return None

        model = "iGrill Unknown"
        for prefix, mapped in _PREFIX_MODEL:
            if name_lower.startswith(prefix):
                model = mapped
                break

        probes = _PROBE_COUNTS.get(model, 4)

        device_id = None
        if "_" in local_name:
            suffix = local_name.rsplit("_", 1)[1]
            if suffix and suffix.lower() not in ("mini", "v2", "v3", "2", "unknown"):
                device_id = suffix

        metadata: dict = {
            "model": model,
            "probes": probes,
        }
        if local_name:
            metadata["local_name"] = local_name
        if device_id is not None:
            metadata["device_id"] = device_id

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:weber_igrill".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="weber_igrill",
            beacon_type="weber_igrill",
            device_class="thermometer",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
