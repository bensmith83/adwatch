"""Apple Nearby Action parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

NEARBY_ACTION_TYPE = 0x0F

ACTION_TYPE_NAMES = {
    0x01: "Apple TV Setup",
    0x04: "Mobile Backup",
    0x05: "Watch Setup",
    0x06: "Apple TV Pair",
    0x07: "Internet Relay",
    0x08: "WiFi Password Sharing",
    0x09: "iOS Setup / Homekit",
    0x0A: "Repair",
    0x0B: "Speaker Setup",
    0x0C: "Apple Pay",
    0x0D: "Whole Home Audio Setup",
    0x0E: "Developer Tools Pairing",
    0x0F: "Answered Call",
    0x10: "Ended Call",
    0x13: "Handoff (Safari)",
    0x14: "Handoff (Keynote)",
    0x27: "Apple TV Connect",
}


@register_parser(
    name="apple_nearby_action",
    company_id=0x004C,
    description="Apple Nearby Action",
    version="1.0",
    core=True,
)
class AppleNearbyActionParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        if tlv_type != NEARBY_ACTION_TYPE:
            return None

        tlv_len = data[3]
        tlv_value = data[4:]
        if len(tlv_value) < 2 or tlv_len < 2:
            return None

        action_flags = tlv_value[0]
        action_type = tlv_value[1]

        payload_hex = tlv_value[:tlv_len].hex()
        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{payload_hex}".encode()
        ).hexdigest()[:16]

        action_type_name = ACTION_TYPE_NAMES.get(
            action_type, f"Unknown (0x{action_type:02x})"
        )

        metadata = {
            "action_flags": action_flags,
            "action_type": action_type,
            "action_type_name": action_type_name,
            "auth_tag_present": bool(action_flags & 0x01),
            "is_sender": bool(action_flags & 0x02),
        }

        if action_type == 0x08 and len(tlv_value) >= 5:
            metadata["ssid_hash_hex"] = tlv_value[2:5].hex()

        return ParseResult(
            parser_name="apple_nearby_action",
            beacon_type="apple_nearby_action",
            device_class="phone",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata=metadata,
        )
