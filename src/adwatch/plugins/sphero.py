"""Sphero robot BLE advertisement parser.

Identifiers per apk-ble-hunting/reports/sphero-sprk_passive.md. Sphero uses
two service-UUID families (v1 pre-BB-8, v2 modern) plus a 6-char local name
of the form `<2-char model prefix>-<4-char unit id>`.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser


# v1 Robot Control service ("Sphero!") used by pre-BB-8 toys.
SPHERO_SERVICE_UUID_V1 = "22bb746f-2ba0-7554-2d6f-726568705327"
# v2 API service ("WOO Sphero!!") used by BOLT, RVR, modern toys.
SPHERO_SERVICE_UUID_V2 = "00010001-574f-4f20-5370-6865726f2121"
# v2 Initializer / AntiDoS service.
SPHERO_SERVICE_UUID_V2_INIT = "00020001-574f-4f20-5370-6865726f2121"

# Backward-compatible alias (was the only UUID in v1.0.0 of this plugin).
SPHERO_SERVICE_UUID = SPHERO_SERVICE_UUID_V2

PREFIX_TO_MODEL = {
    "BB": "BB-8",
    "GB": "BB-9E",
    "SK": "SPRK+",
    "SB": "BOLT",
    "SM": "Mini",
    "RV": "RVR",
}

SPHERO_NAME_RE = re.compile(r"^(BB|GB|SK|SB|SM|RV)-([A-Z0-9]{4})$")


@register_parser(
    name="sphero",
    service_uuid=[
        SPHERO_SERVICE_UUID_V1,
        SPHERO_SERVICE_UUID_V2,
        SPHERO_SERVICE_UUID_V2_INIT,
    ],
    local_name_pattern=SPHERO_NAME_RE.pattern,
    description="Sphero robot advertisements",
    version="1.1.0",
    core=False,
)
class SpherParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = any(
            u in (raw.service_uuids or [])
            for u in (SPHERO_SERVICE_UUID_V1, SPHERO_SERVICE_UUID_V2, SPHERO_SERVICE_UUID_V2_INIT)
        )
        name_match = raw.local_name and SPHERO_NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        metadata: dict = {}
        if name_match:
            prefix = name_match.group(1)
            metadata["model"] = PREFIX_TO_MODEL.get(prefix, prefix)
            metadata["device_id"] = name_match.group(2)
            metadata["device_name"] = raw.local_name
        else:
            # UUID-only match; specific model unknown from just UUID (the v2
            # UUID covers BOLT/RVR/modern toys — don't guess one).
            metadata["model"] = "unknown"

        if name_match:
            id_basis = f"sphero:{name_match.group(1)}-{name_match.group(2)}"
        else:
            id_basis = f"sphero:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="sphero",
            beacon_type="sphero",
            device_class="toy",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
