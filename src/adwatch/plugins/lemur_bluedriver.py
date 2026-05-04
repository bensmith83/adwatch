"""Lemur Monitors BlueDriver / VHC OBD-II dongle plugin.

Per apk-ble-hunting/reports/lemurmonitors-bluedriver_passive.md:

  - Service UUID a9da6040-0823-4995-94ec-9ce41ca28833 (vendor-assigned).
  - Local name: 'BlueDriver' or starts with 'BlueDriver-' (older), or
    'VHC ' / 'VHC<suffix>' (newer Vehicle Health Check).
  - No manufacturer/service-data telemetry — pure presence beacon.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


BLUEDRIVER_SERVICE_UUID = "a9da6040-0823-4995-94ec-9ce41ca28833"
_NAME_RE = re.compile(r"^(BlueDriver|VHC)", re.IGNORECASE)


@register_parser(
    name="lemur_bluedriver",
    service_uuid=BLUEDRIVER_SERVICE_UUID,
    local_name_pattern=r"(?i)^(BlueDriver|VHC)",
    description="Lemur BlueDriver / VHC OBD-II dongle",
    version="1.0.0",
    core=False,
)
class LemurBluedriverParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = BLUEDRIVER_SERVICE_UUID in normalized
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (uuid_hit or name_match):
            return None

        metadata: dict = {}
        if name_match:
            metadata["device_name"] = raw.local_name
            brand = name_match.group(1).lower()
            metadata["product_family"] = "vhc" if brand == "vhc" else "bluedriver"
        elif uuid_hit:
            metadata["product_family"] = "unknown"

        id_hash = hashlib.sha256(
            f"lemur_bluedriver:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="lemur_bluedriver",
            beacon_type="lemur_bluedriver",
            device_class="obd2",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
