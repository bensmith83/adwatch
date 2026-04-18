"""Kinsa Polaris smart thermometer BLE advertisement parser.

Per apk-ble-hunting/reports/kinsa-polaris-app_passive.md. Service UUID base
`00000000-XXXX-746c-6165-4861736e694b` ("Kinsa Health" in ASCII) plus name-
prefix filter for Kinsa / AViTA / KS_ devices.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Base: `XXXX-746c-6165-4861736e694b` is ASCII "tlea Hasni K" backwards,
# which decodes the vendor signature.
_KINSA_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-746c-6165-4861736e694b$"
)


@register_parser(
    name="kinsa",
    local_name_pattern=r"^(Kinsa|AViTA|KS_)",
    description="Kinsa Polaris smart thermometers",
    version="1.0.0",
    core=False,
)
class KinsaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_match = any(name.startswith(p) for p in ("Kinsa", "AViTA", "KS_"))

        matched_uuid = None
        for u in (raw.service_uuids or []):
            if _KINSA_UUID_RE.match(u.lower()):
                matched_uuid = u.lower()
                break

        if not name_match and not matched_uuid:
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if matched_uuid:
            metadata["service_uuid"] = matched_uuid

        id_hash = hashlib.sha256(f"kinsa:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="kinsa",
            beacon_type="kinsa",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
