"""Greenworks Optimow BLE advertisement parser.

Per apk-ble-hunting/reports/greenworks-tools_passive.md. Company ID 0x15A8
(unregistered, distinctive) + name contains greenworks / gwelite / cramer +
optional OUI prefixes 34:12:XX, 45:09:XX, A8:15:XX.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


GREENWORKS_COMPANY_ID = 0x15A8
MAC_PREFIXES = ("34:12:", "45:09:", "A8:15:")

_GREENWORKS_NAME_RE = re.compile(r"(?i)greenworks|gwelite|cramer")


@register_parser(
    name="greenworks",
    company_id=GREENWORKS_COMPANY_ID,
    mac_prefix=MAC_PREFIXES,
    local_name_pattern=_GREENWORKS_NAME_RE.pattern,
    description="Greenworks / Cramer / GwElite outdoor tools (mowers, blowers)",
    version="1.0.0",
    core=False,
)
class GreenworksParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == GREENWORKS_COMPANY_ID
        )
        name = raw.local_name or ""
        name_match = bool(_GREENWORKS_NAME_RE.search(name))
        mac_match = any(raw.mac_address.upper().startswith(p) for p in MAC_PREFIXES)

        if not (has_company or name_match or mac_match):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
            if re.search(r"(?i)cramer", name):
                metadata["brand"] = "Cramer"
            elif re.search(r"(?i)gwelite", name):
                metadata["brand"] = "GwElite"
            else:
                metadata["brand"] = "Greenworks"
        if has_company:
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()
        if mac_match:
            metadata["mac_oui_match"] = True

        id_hash = hashlib.sha256(
            f"greenworks:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="greenworks",
            beacon_type="greenworks",
            device_class="outdoor_tool",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
