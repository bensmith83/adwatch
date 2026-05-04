"""Fellow kettle plugin (Stagg EKG Pro / Corvo EKG).

Per apk-ble-hunting/reports/fellowapp_passive.md: Fellow's kettles are
ESP32-based and advertise a custom 128-bit primary service UUID. The
companion app filters by service UUID; an aux UUID also appears in some
ads (likely OTA / provisioning). Mfr-data is not used in static analysis;
the local-name carries the model and may include a MAC-suffix tail like
``Stagg EKG Pro-A1B2``.

Matching is OR over (primary UUID, aux UUID, name regex). Day-to-day the
kettle may stop advertising once Wi-Fi-paired; a hit therefore means the
device is in pair / setup mode.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


FELLOW_PRIMARY_UUID = "2291c4b6-5d7f-4477-a88b-b266edb97142"
FELLOW_AUX_UUID = "7aebf330-6cb1-46e4-b23b-7cc2262c605e"

_MODEL_PATTERNS = [
    ("Stagg EKG Pro", re.compile(r"^Stagg EKG Pro")),
    ("Corvo EKG", re.compile(r"^Corvo EKG")),
    ("Fellow EKG Pro", re.compile(r"^Fellow EKG Pro")),
]

_SUFFIX_RE = re.compile(r"-([0-9A-Fa-f]{2,8})$")


@register_parser(
    name="fellow",
    service_uuid=[FELLOW_PRIMARY_UUID, FELLOW_AUX_UUID],
    local_name_pattern=r"^(Stagg EKG Pro|Corvo EKG|Fellow EKG Pro)",
    description="Fellow Stagg / Corvo kettles",
    version="1.0.0",
    core=False,
)
class FellowParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        primary_hit = FELLOW_PRIMARY_UUID in normalized
        aux_hit = FELLOW_AUX_UUID in normalized
        local_name = raw.local_name or ""

        model: str | None = None
        for name, pat in _MODEL_PATTERNS:
            if pat.match(local_name):
                model = name
                break

        if not (primary_hit or aux_hit or model):
            return None

        metadata: dict = {"vendor": "Fellow"}
        if model:
            metadata["model"] = model
            metadata["device_name"] = local_name
        if aux_hit:
            metadata["aux_service_seen"] = True

        suffix: str | None = None
        if model:
            m = _SUFFIX_RE.search(local_name)
            if m:
                suffix = m.group(1).upper()
                metadata["mac_suffix"] = suffix

        if suffix:
            id_basis = f"fellow:{suffix}"
        else:
            id_basis = f"fellow:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fellow",
            beacon_type="fellow",
            device_class="kettle",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
