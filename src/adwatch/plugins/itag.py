"""iTAG BLE anti-loss tracker plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ITAG_UUIDS = ["ffe0", "1802"]


@register_parser(
    name="itag",
    service_uuid=ITAG_UUIDS,
    local_name_pattern=r"(?i)^iTAG",
    description="iTAG anti-loss tracker",
    version="1.0.0",
    core=False,
)
class ITagParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        matched = False

        for uuid in ITAG_UUIDS:
            if (raw.service_uuids and uuid in raw.service_uuids) or (
                raw.service_data and uuid in raw.service_data
            ):
                matched = True
                break

        if not matched and raw.local_name and raw.local_name.lower().startswith("itag"):
            matched = True

        if not matched:
            return None

        metadata = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"{raw.mac_address}:itag".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="itag",
            beacon_type="itag",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
