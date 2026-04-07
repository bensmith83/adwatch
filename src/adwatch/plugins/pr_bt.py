"""PR BT portable Bluetooth device advertisement parser.

PR BT devices advertise with a custom service UUID
4553867F-F809-49F4-AEFC-E190A1F459F3 alongside the standard Device
Information service (180A). The local name follows the pattern
"PR BT XXXX" where XXXX is a hex device identifier.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

PR_BT_SERVICE_UUID = "4553867f-f809-49f4-aefc-e190a1f459f3"
NAME_RE = re.compile(r"^PR BT\s+([0-9A-Fa-f]+)")


@register_parser(
    name="pr_bt",
    service_uuid=PR_BT_SERVICE_UUID,
    local_name_pattern=r"^PR BT\s",
    description="PR BT portable device advertisements",
    version="1.0.0",
    core=False,
)
class PrBtParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = PR_BT_SERVICE_UUID in (raw.service_uuids or [])
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)

        if not uuid_match and not name_match:
            return None

        id_hash = hashlib.sha256(f"pr_bt:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if name_match:
            metadata["device_id"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="pr_bt",
            beacon_type="pr_bt",
            device_class="peripheral",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
