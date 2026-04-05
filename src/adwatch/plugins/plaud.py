"""PLAUD AI recorder BLE advertisement parser.

Supports PLAUD NOTE and PLAUD NotePin devices. These are AI-powered
voice recorders that advertise via BLE with manufacturer-specific data.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

PLAUD_NAME_RE = re.compile(r"^PLAUD[\s_](\S+)")


@register_parser(
    name="plaud",
    local_name_pattern=r"^PLAUD[\s_]",
    description="PLAUD AI recorder advertisements",
    version="1.0.0",
    core=False,
)
class PlaudParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        m = PLAUD_NAME_RE.match(raw.local_name)
        if not m:
            return None

        model = m.group(1)
        id_hash = hashlib.sha256(f"plaud:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {
            "device_name": raw.local_name,
            "model": model,
        }

        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            metadata["company_id"] = raw.company_id

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="plaud",
            beacon_type="plaud",
            device_class="recorder",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
