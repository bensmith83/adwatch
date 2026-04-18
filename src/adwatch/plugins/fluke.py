"""Fluke Connect multimeter BLE advertisement parser.

Per apk-ble-hunting/reports/fluke-deviceapp_passive.md. Service-UUID base
`b698XXXX-7562-11e2-b50d-00163e46f8fe` — variable XXXX per instrument family.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


_FLUKE_UUID_RE = re.compile(
    r"^b698[0-9a-f]{4}-7562-11e2-b50d-00163e46f8fe$"
)


@register_parser(
    name="fluke",
    local_name_pattern=r"(?i)^Fluke",
    description="Fluke Connect multimeters / instruments",
    version="1.0.0",
    core=False,
)
class FlukeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        matched_uuid = None
        for u in (raw.service_uuids or []):
            if _FLUKE_UUID_RE.match(u.lower()):
                matched_uuid = u.lower()
                break

        name = raw.local_name or ""
        name_match = name.lower().startswith("fluke")

        if not matched_uuid and not name_match:
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if matched_uuid:
            metadata["service_uuid"] = matched_uuid
            # Variable XXXX field = instrument family.
            metadata["instrument_family_code"] = matched_uuid[4:8]

        id_hash = hashlib.sha256(f"fluke:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fluke",
            beacon_type="fluke",
            device_class="measuring_tool",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
