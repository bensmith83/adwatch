"""Kegtron beer keg monitor plugin."""

import hashlib
import re
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

KEGTRON_NAME_RE = re.compile(r"^(Kegtron|KT-)")


@register_parser(
    name="kegtron",
    company_id=0xFFFF,
    local_name_pattern=r"^(Kegtron|KT-)",
    description="Kegtron beer keg monitor",
    version="1.0.0",
    core=False,
)
class KegtronParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Must validate local_name since 0xFFFF is generic
        if not raw.local_name or not KEGTRON_NAME_RE.match(raw.local_name):
            return None

        if not raw.manufacturer_data or len(raw.manufacturer_data) < 9:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 7:
            return None

        port = payload[0]
        keg_size = struct.unpack_from("<H", payload, 1)[0]
        vol_start = struct.unpack_from("<H", payload, 3)[0]
        vol_dispensed = struct.unpack_from("<H", payload, 5)[0]

        vol_remaining = vol_start - vol_dispensed
        pct_remaining = (vol_remaining / keg_size * 100) if keg_size > 0 else 0.0

        # Port name: null-terminated string after the 7 fixed bytes
        port_name = ""
        if len(payload) > 7:
            name_bytes = payload[7:]
            null_idx = name_bytes.find(0x00)
            if null_idx > 0:
                port_name = name_bytes[:null_idx].decode("utf-8", errors="ignore")
            elif null_idx < 0 and len(name_bytes) > 0:
                port_name = name_bytes.decode("utf-8", errors="ignore")

        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="kegtron",
            beacon_type="kegtron",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "port": port,
                "keg_size_ml": keg_size,
                "volume_dispensed_ml": vol_dispensed,
                "volume_remaining_ml": vol_remaining,
                "percent_remaining": round(pct_remaining, 2),
                "port_name": port_name,
            },
        )

    def storage_schema(self):
        return None
