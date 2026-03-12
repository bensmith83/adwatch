"""Apple Continuity parser (Nearby Info, Handoff, HomeKit, Siri, etc.)."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

NEARBY_INFO_TYPE = 0x10
HANDOFF_TYPE = 0x0C
HOMEKIT_TYPE = 0x06
HEY_SIRI_TYPE = 0x08
MAGIC_SWITCH_TYPE = 0x0B
TETHERING_TARGET_TYPE = 0x0D
TETHERING_SOURCE_TYPE = 0x0E

ACTION_CODES = {
    0x00: "Activity Unknown",
    0x01: "Reporting Disabled",
    0x03: "Idle User",
    0x05: "Audio Playing (screen locked)",
    0x07: "Active User (screen on)",
    0x09: "Screen On + Video",
    0x0A: "Watch on wrist/unlocked",
    0x0B: "Recent User Interaction",
}

KNOWN_TLV_TYPES = {
    NEARBY_INFO_TYPE, HANDOFF_TYPE, HOMEKIT_TYPE,
    HEY_SIRI_TYPE, MAGIC_SWITCH_TYPE,
    TETHERING_TARGET_TYPE, TETHERING_SOURCE_TYPE,
}


@register_parser(
    name="apple_continuity",
    company_id=0x004C,
    description="Apple Continuity (Nearby Info / Handoff / HomeKit / Siri / Tethering)",
    version="2.0",
    core=True,
)
class AppleContinuityParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        tlv_len = data[3]
        tlv_value = data[4:]

        if tlv_type not in KNOWN_TLV_TYPES:
            return None

        if tlv_type == NEARBY_INFO_TYPE:
            return self._parse_nearby_info(raw, tlv_len, tlv_value, data)
        elif tlv_type == HANDOFF_TYPE:
            return self._parse_handoff(raw, tlv_len, tlv_value, data)
        elif tlv_type == HOMEKIT_TYPE:
            return self._parse_homekit(raw, tlv_len, tlv_value, data)
        elif tlv_type == HEY_SIRI_TYPE:
            return self._parse_hey_siri(raw, tlv_len, tlv_value, data)
        elif tlv_type == MAGIC_SWITCH_TYPE:
            return self._parse_magic_switch(raw, tlv_len, tlv_value, data)
        elif tlv_type == TETHERING_TARGET_TYPE:
            return self._parse_tethering(raw, tlv_len, tlv_value, data, "apple_tethering")
        elif tlv_type == TETHERING_SOURCE_TYPE:
            return self._parse_tethering(raw, tlv_len, tlv_value, data, "apple_tethering_source")
        return None

    def _parse_nearby_info(self, raw, tlv_len, tlv_value, data):
        if len(tlv_value) < tlv_len or tlv_len < 3:
            return None

        status_action = tlv_value[0]
        status_flags = (status_action >> 4) & 0x0F
        action_code = status_action & 0x0F

        ios_version = tlv_value[1]
        auth_tag = tlv_value[2:tlv_len].hex()

        device_class = "watch" if action_code == 0x0A else "phone"
        action_name = ACTION_CODES.get(action_code, f"Unknown (0x{action_code:02X})")

        status_details = {
            "airpods_connected": bool(status_flags & 0x01),
            "wifi_on": bool(status_flags & 0x02),
            "primary_icloud": bool(status_flags & 0x04),
            "auth_tag_type": bool(status_flags & 0x08),
        }

        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{auth_tag}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_continuity",
            beacon_type="apple_nearby",
            device_class=device_class,
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "action_code": action_code,
                "action_name": action_name,
                "status_flags": status_flags,
                "status_details": status_details,
                "ios_version": ios_version,
                "auth_tag": auth_tag,
            },
        )

    def _parse_handoff(self, raw, tlv_len, tlv_value, data):
        if len(tlv_value) < tlv_len:
            return None

        payload_hex = tlv_value[:tlv_len].hex()
        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{payload_hex}".encode()
        ).hexdigest()[:16]

        metadata = {}
        if len(tlv_value) >= 1:
            first_byte = tlv_value[0]
            if first_byte == 0x08:
                metadata["clipboard_status"] = "present"
            elif first_byte == 0x00:
                metadata["clipboard_status"] = "none"
            else:
                metadata["clipboard_status"] = "unknown"
        if len(tlv_value) >= 2:
            metadata["sequence_number"] = tlv_value[1]

        return ParseResult(
            parser_name="apple_continuity",
            beacon_type="apple_handoff",
            device_class="phone",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata=metadata,
        )

    def _parse_homekit(self, raw, tlv_len, tlv_value, data):
        if len(tlv_value) < tlv_len or tlv_len < 3:
            return None

        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{tlv_value[:tlv_len].hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_continuity",
            beacon_type="apple_homekit",
            device_class="iot",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "category": tlv_value[0],
                "state": tlv_value[1],
                "config_number": tlv_value[2],
            },
        )

    def _parse_hey_siri(self, raw, tlv_len, tlv_value, data):
        if len(tlv_value) < tlv_len or tlv_len < 4:
            return None

        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{tlv_value[:tlv_len].hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_continuity",
            beacon_type="apple_siri",
            device_class="phone",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "perceptual_hash": int.from_bytes(tlv_value[0:2], "big"),
                "snr": tlv_value[2],
                "confidence": tlv_value[3],
            },
        )

    def _parse_magic_switch(self, raw, tlv_len, tlv_value, data):
        if len(tlv_value) < tlv_len:
            return None

        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{tlv_value[:tlv_len].hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_continuity",
            beacon_type="apple_magic_switch",
            device_class="phone",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "data": tlv_value[:tlv_len].hex(),
            },
        )

    def _parse_tethering(self, raw, tlv_len, tlv_value, data, beacon_type):
        if len(tlv_value) < tlv_len or tlv_len < 2:
            return None

        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{tlv_value[:tlv_len].hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_continuity",
            beacon_type=beacon_type,
            device_class="phone",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "signal_strength": tlv_value[0],
                "battery": tlv_value[1],
            },
        )
