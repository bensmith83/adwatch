"""Google Fast Pair BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

FAST_PAIR_UUID = "fe2c"

MODEL_NAMES = {
    "aabb11": "Pixel Buds Pro",
    "f52800": "Pixel Buds A-Series",
    "718c17": "JBL Live Pro 2",
    "0600d4": "Sony WH-1000XM5",
    "060000": "Google Pixel Buds",
    "070000": "Galaxy Buds Live",
    "d40068": "Beats Studio Buds",
}


@register_parser(
    name="fast_pair",
    service_uuid=FAST_PAIR_UUID,
    description="Google Fast Pair accessory advertisements",
    version="1.0.0",
    core=True,
)
class FastPairParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or FAST_PAIR_UUID not in raw.service_data:
            return None

        data = raw.service_data[FAST_PAIR_UUID]
        if not data:
            return None

        if len(data) == 3:
            return self._parse_discoverable(raw, data)
        elif len(data) >= 2:
            return self._parse_not_discoverable(raw, data)

        return None

    def _parse_discoverable(self, raw: RawAdvertisement, data: bytes) -> ParseResult:
        model_id = data.hex()
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{model_id}".encode()
        ).hexdigest()[:16]

        model_name = MODEL_NAMES.get(model_id, "Unknown")

        return ParseResult(
            parser_name="fast_pair",
            beacon_type="fast_pair_discoverable",
            device_class="accessory",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={"model_id": model_id, "model_name": model_name, "mode": "discoverable"},
        )

    def _parse_not_discoverable(self, raw: RawAdvertisement, data: bytes) -> ParseResult:
        flags = data[0]
        ll = flags & 0x03
        filter_len = [0, 1, 2, 4][ll]

        filter_bytes = data[1:1 + filter_len]
        salt_offset = 1 + filter_len
        salt_bytes = data[salt_offset:salt_offset + 1]
        remaining = data[salt_offset + 1:]

        filter_hex = filter_bytes.hex()
        salt_hex = salt_bytes.hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{filter_hex}:{salt_hex}".encode()
        ).hexdigest()[:16]

        metadata = {
            "mode": "not_discoverable",
            "account_key_filter": filter_hex,
            "salt": salt_hex,
        }

        if len(remaining) >= 4:
            type_nibble = (remaining[0] >> 4) & 0x0F
            if type_nibble in (0x03, 0x04):
                left_raw, right_raw, case_raw = remaining[1], remaining[2], remaining[3]
                metadata["battery_left"] = (left_raw & 0x7F) if (left_raw & 0x7F) != 0x7F else None
                metadata["battery_right"] = (right_raw & 0x7F) if (right_raw & 0x7F) != 0x7F else None
                metadata["battery_case"] = (case_raw & 0x7F) if (case_raw & 0x7F) != 0x7F else None
                metadata["charging_left"] = bool(left_raw & 0x80)
                metadata["charging_right"] = bool(right_raw & 0x80)
                metadata["charging_case"] = bool(case_raw & 0x80)
                metadata["battery_show_ui"] = type_nibble == 0x03

        return ParseResult(
            parser_name="fast_pair",
            beacon_type="fast_pair_not_discoverable",
            device_class="accessory",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
