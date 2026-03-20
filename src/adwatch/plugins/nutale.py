"""Nutale tracker BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

NUTALE_NAME_RE = re.compile(r"^Nutale")


@register_parser(
    name="nutale",
    local_name_pattern=r"^Nutale",
    description="Nutale tracker advertisements",
    version="1.0.0",
    core=False,
)
class NutaleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.local_name is None or not NUTALE_NAME_RE.search(raw.local_name):
            return None

        id_hash = hashlib.sha256(f"nutale:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="nutale",
            beacon_type="nutale",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata={"device_name": raw.local_name},
        )
