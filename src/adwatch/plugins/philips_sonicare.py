"""Philips Sonicare toothbrush BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SONICARE_UUID = "477ea600-a260-11e4-ae37-0002a5d50001"
SONICARE_NAME_RE = re.compile(r"Sonicare")


@register_parser(
    name="philips_sonicare",
    service_uuid=SONICARE_UUID,
    local_name_pattern=r"Sonicare",
    description="Philips Sonicare toothbrush advertisements",
    version="1.0.0",
    core=False,
)
class PhilipsSonicareParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = SONICARE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and SONICARE_NAME_RE.search(raw.local_name)

        if not uuid_match and not name_match:
            return None

        name = raw.local_name or ""
        id_hash = hashlib.sha256(f"{raw.mac_address}:{name}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="philips_sonicare",
            beacon_type="philips_sonicare",
            device_class="personal_care",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
