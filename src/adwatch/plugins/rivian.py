"""Rivian vehicle and phone key BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

RIVIAN_COMPANY_ID = 0x0941
RIVIAN_NAME_RE = re.compile(r"^Rivian|^RIVN")

MODE_MAP = {
    0x01: "phone_key",
    0x17: "vehicle",
}

DEVICE_CLASS_MAP = {
    "phone_key": "vehicle_key",
    "vehicle": "vehicle",
    "passive": "vehicle",
}


@register_parser(
    name="rivian",
    company_id=RIVIAN_COMPANY_ID,
    local_name_pattern=r"^Rivian|^RIVN",
    description="Rivian vehicle and phone key advertisements",
    version="1.0.0",
    core=False,
)
class RivianParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_mfr = False
        mode = "passive"

        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id == RIVIAN_COMPANY_ID:
                has_mfr = True
                if len(raw.manufacturer_data) >= 3:
                    mode_byte = raw.manufacturer_data[2]
                    mode = MODE_MAP.get(mode_byte, "passive")

        name_match = raw.local_name is not None and RIVIAN_NAME_RE.search(raw.local_name)

        if not has_mfr and not name_match:
            return None

        device_class = DEVICE_CLASS_MAP.get(mode, "vehicle")

        id_hash = hashlib.sha256(f"rivian:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {"mode": mode}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        return ParseResult(
            parser_name="rivian",
            beacon_type="rivian",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data[2:].hex() if raw.manufacturer_data and len(raw.manufacturer_data) > 2 else "",
            metadata=metadata,
        )
