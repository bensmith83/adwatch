"""iRobot Roomba / Braava BLE advertisement parser.

Per apk-ble-hunting/reports/irobot-home_passive.md. Detection via name match,
service UUID `0bd51777-…`, or manufacturer-data magic byte pattern.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


IROBOT_SERVICE_UUID = "0bd51777-e7cb-469b-8e4d-2742f1ba77cc"

# Magic mfr-data signature per passive report: `A8 01 ?? 31 10` (bytes 0-4 of
# raw mfr data including company_id; company_id here is 0x01A8 = 424 dec).
_IROBOT_MFR_COMPANY_ID = 0x01A8
_IROBOT_MFR_MAGIC_B3_B4 = (0x31, 0x10)

_IROBOT_NAME_RE = re.compile(r"^(Altadena|iRobot Braav|iRobot Braava|Roomba)")


@register_parser(
    name="irobot",
    company_id=_IROBOT_MFR_COMPANY_ID,
    service_uuid=IROBOT_SERVICE_UUID,
    local_name_pattern=_IROBOT_NAME_RE.pattern,
    description="iRobot Roomba and Braava robots",
    version="1.0.0",
    core=False,
)
class IRobotParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_match = bool(_IROBOT_NAME_RE.match(name))
        has_uuid = IROBOT_SERVICE_UUID in [u.lower() for u in (raw.service_uuids or [])]

        has_mfr_magic = False
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 5:
            if int.from_bytes(raw.manufacturer_data[:2], "little") == _IROBOT_MFR_COMPANY_ID:
                if (raw.manufacturer_data[3], raw.manufacturer_data[4]) == _IROBOT_MFR_MAGIC_B3_B4:
                    has_mfr_magic = True

        # Since iRobot shares company ID 0x01A8 with Mammotion, only claim it
        # here if the magic bytes 0x31 0x10 follow, or we have a UUID/name match.
        if not (name_match or has_uuid or has_mfr_magic):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if has_mfr_magic:
            metadata["mfr_magic_match"] = True
        if has_uuid:
            metadata["has_irobot_service"] = True

        id_hash = hashlib.sha256(f"irobot:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="irobot",
            beacon_type="irobot",
            device_class="vacuum",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )
