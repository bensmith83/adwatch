"""TP-Link Tapo/Kasa smart home BLE plugin."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

_PATTERN = re.compile(r"(?i)^(Tapo|Kasa|TP-LINK)")

_PRODUCT_LINE_MAP = {
    "tapo": "Tapo",
    "kasa": "Kasa",
    "tp-link": "TP-Link",
}

_CATEGORY_MAP = {
    "P": "smart_plug",
    "L": "smart_bulb",
    "C": "camera",
    "H": "hub",
    "T": "sensor",
}


@register_parser(
    name="tplink_tapo",
    local_name_pattern=r"(?i)^(Tapo|Kasa|TP-LINK)",
    description="TP-Link Tapo/Kasa smart home advertisements",
    version="1.0.0",
    core=False,
)
class TpLinkTapoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None)
        if not local_name:
            return None

        m = _PATTERN.match(local_name)
        if not m:
            return None

        prefix = m.group(1).lower()
        product_line = _PRODUCT_LINE_MAP.get(prefix, prefix)

        # Split on underscore to get model (second component)
        parts = local_name.split("_")
        model = parts[1] if len(parts) > 1 else None

        # Category from model first char
        category = "smart_home"
        if model:
            category = _CATEGORY_MAP.get(model[0].upper(), "smart_home")

        metadata = {
            "product_line": product_line,
            "category": category,
            "local_name": local_name,
        }
        if model:
            metadata["model"] = model

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:tplink_tapo".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="tplink_tapo",
            beacon_type="tplink_tapo",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
