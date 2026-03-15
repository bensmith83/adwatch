"""Teltonika EYE Sensor (BTSMP1) industrial multi-sensor plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

TELTONIKA_COMPANY_ID = 0x089A

# (flag_bit, key, size_bytes, parse_func)
_FIELDS = [
    (0x01, "temperature", 2, lambda d, o: struct.unpack_from("<h", d, o)[0] / 100.0),
    (0x02, "humidity", 1, lambda d, o: d[o]),
    (0x04, "magnet_detected", 1, lambda d, o: bool(d[o])),
    (0x08, "movement_count", 2, lambda d, o: struct.unpack_from("<H", d, o)[0]),
    (0x10, "pitch", 2, lambda d, o: float(struct.unpack_from("<h", d, o)[0])),
    (0x20, "roll", 2, lambda d, o: float(struct.unpack_from("<h", d, o)[0])),
    (0x40, "battery_mv", 2, lambda d, o: 2000 + struct.unpack_from("<H", d, o)[0] * 10),
]


@register_parser(
    name="teltonika_eye",
    company_id=TELTONIKA_COMPANY_ID,
    description="Teltonika EYE Sensor industrial multi-sensor",
    version="1.0.0",
    core=False,
)
class TeltonikEyeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != TELTONIKA_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 2:
            return None

        flags = payload[1]
        data = payload[2:]
        offset = 0
        metadata = {}

        for flag_bit, key, size, parse_func in _FIELDS:
            if flags & flag_bit:
                if offset + size > len(data):
                    return None
                metadata[key] = parse_func(data, offset)
                offset += size

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:teltonika_eye".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="teltonika_eye",
            beacon_type="teltonika_eye",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
