"""ELK-BLEDOM LED light strip BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ELK_NAME_RE = re.compile(r"^ELK-BLEDOM")


@register_parser(
    name="elk_bledom",
    local_name_pattern=r"^ELK-BLEDOM",
    description="ELK-BLEDOM LED light strip advertisements",
    version="1.0.0",
    core=False,
)
class ElkBledomParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.local_name is None or not ELK_NAME_RE.search(raw.local_name):
            return None

        id_hash = hashlib.sha256(f"elk_bledom:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="elk_bledom",
            beacon_type="elk_bledom",
            device_class="light",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata={"device_name": raw.local_name},
        )
