"""Abbott FreeStyle Libre 3 CGM BLE advertisement parser.

Per apk-ble-hunting/reports/freestylelibre3-app-us_passive.md. The Libre 3 app
uses direct-connect-by-MAC post-NFC in normal operation, so BLE adverts are
brief. Primary passive signal is the Abbott Libre 3 UUID base
`0898XXXX-ef89-11e9-81b4-2a2ae2dbcce4` and/or the device-name pattern.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Known Libre 3 GATT characteristic/service UUIDs all share the same base.
LIBRE3_UUID_BASE_RE = re.compile(
    r"^0898[0-9a-f]{4}-ef89-11e9-81b4-2a2ae2dbcce4$"
)

# Observed / documented name formats.
_LIBRE3_NAME_RE = re.compile(r"^(?:FreeStyle Libre 3|ABBOTT|LIBRE3)", re.IGNORECASE)


@register_parser(
    name="freestyle_libre3",
    local_name_pattern=r"^(?i:FreeStyle Libre 3|ABBOTT|LIBRE3)",
    description="Abbott FreeStyle Libre 3 CGM",
    version="1.0.0",
    core=False,
)
class FreeStyleLibre3Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_match = bool(_LIBRE3_NAME_RE.match(name))

        uuid_match = False
        matched_uuid = None
        for u in (raw.service_uuids or []):
            if LIBRE3_UUID_BASE_RE.match(u.lower()):
                uuid_match = True
                matched_uuid = u.lower()
                break

        if not (name_match or uuid_match):
            return None

        metadata: dict = {"model": "FreeStyle Libre 3"}
        if name:
            metadata["device_name"] = name
        if matched_uuid:
            metadata["abbott_uuid"] = matched_uuid

        id_hash = hashlib.sha256(
            f"libre3:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="freestyle_libre3",
            beacon_type="freestyle_libre3",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
