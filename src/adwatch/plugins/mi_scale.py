"""Xiaomi Mi Scale (v1 + v2 Body Composition) plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="mi_scale",
    service_uuid="181d",
    local_name_pattern=r"^(MIBFS|XMTZC)",
    description="Xiaomi Mi Scale (v1 weight, v2 body composition)",
    version="1.0.0",
    core=False,
)
class MiScaleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        data = None
        version = 1
        if "181b" in raw.service_data:
            data = raw.service_data["181b"]
            version = 2
        elif "181d" in raw.service_data:
            data = raw.service_data["181d"]
            version = 1
        else:
            return None

        min_len = 13 if version == 2 else 11
        if not data or len(data) < min_len:
            return None

        flags = struct.unpack_from("<H", data, 0)[0]
        is_lbs = bool(flags & 0x01)
        stabilized = bool(flags & 0x10)
        weight_removed = bool(flags & 0x20)

        weight_raw = struct.unpack_from("<H", data, 9)[0]

        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        metadata = {
            "stabilized": stabilized,
            "weight_removed": weight_removed,
            "version": version,
        }

        if is_lbs:
            metadata["unit"] = "lbs"
            metadata["weight_lbs"] = weight_raw / 100.0
        else:
            metadata["unit"] = "kg"
            metadata["weight_kg"] = weight_raw / 200.0

        if version == 2:
            impedance = struct.unpack_from("<H", data, 11)[0]
            metadata["impedance"] = impedance

        return ParseResult(
            parser_name="mi_scale",
            beacon_type="mi_scale",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
