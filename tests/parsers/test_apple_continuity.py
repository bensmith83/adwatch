"""Tests for Apple Continuity parser (Nearby Info + Handoff + new types)."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.apple_continuity import AppleContinuityParser


@pytest.fixture
def parser():
    return AppleContinuityParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# Nearby Info: iPhone active (screen on), action_code=0x07
# 4c 00 10 05 37 18 a1 b2 c3
NEARBY_INFO_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x10,        # Type: Nearby Info
    0x05,        # Length: 5
    0x37,        # status_flags=0x3, action_code=0x7 (active)
    0x18,        # data_flags
    0xA1, 0xB2, 0xC3,  # auth_tag
])

# Handoff: 8-byte encrypted payload
HANDOFF_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x0C,        # Type: Handoff
    0x08,        # Length: 8
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,  # encrypted payload
])

# Apple Watch unlocked
WATCH_PAYLOAD = bytes([
    0x4C, 0x00,
    0x10, 0x05,
    0x1A,        # status_flags=0x1, action_code=0xA (watch unlocked)
    0x98,        # data_flags (unlocked watch)
    0xD4, 0xE5, 0xF6,  # auth_tag
])


# Handoff with clipboard present (0x08) and sequence number 0x42
HANDOFF_CLIPBOARD_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x0C,        # Type: Handoff
    0x08,        # Length: 8
    0x08,        # clipboard status: present
    0x42,        # sequence number
    0x03, 0x04, 0x05, 0x06, 0x07, 0x08,  # rest of payload
])

# Handoff with no clipboard (0x00)
HANDOFF_NO_CLIPBOARD_PAYLOAD = bytes([
    0x4C, 0x00,
    0x0C, 0x04,
    0x00,        # clipboard status: none
    0x10,        # sequence number
    0x01, 0x02,
])

# HomeKit payload
HOMEKIT_PAYLOAD = bytes([
    0x4C, 0x00,
    0x06,        # Type: HomeKit
    0x03,        # Length: 3
    0x02,        # category
    0x01,        # state
    0x05,        # config_number
])

# Hey Siri payload
HEY_SIRI_PAYLOAD = bytes([
    0x4C, 0x00,
    0x08,        # Type: Hey Siri
    0x04,        # Length: 4
    0x12, 0x34,  # perceptual_hash (uint16 BE = 0x1234)
    0x0A,        # snr
    0x63,        # confidence
])

# Magic Switch payload
MAGIC_SWITCH_PAYLOAD = bytes([
    0x4C, 0x00,
    0x0B,        # Type: Magic Switch
    0x03,        # Length: 3
    0xAA, 0xBB, 0xCC,
])

# Tethering Target payload
TETHERING_TARGET_PAYLOAD = bytes([
    0x4C, 0x00,
    0x0D,        # Type: Tethering Target
    0x02,        # Length: 2
    0xC8,        # signal_strength
    0x4B,        # battery
])

# Tethering Source payload
TETHERING_SOURCE_PAYLOAD = bytes([
    0x4C, 0x00,
    0x0E,        # Type: Tethering Source
    0x02,        # Length: 2
    0xD0,        # signal_strength
    0x32,        # battery
])


class TestNearbyInfo:
    def test_parse_valid_nearby_info(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_continuity"

    def test_beacon_type_nearby(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_nearby"

    def test_device_class_phone(self, parser):
        """Normal action codes should yield device_class='phone'."""
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_device_class_watch(self, parser):
        """Action code 0x0A should yield device_class='watch'."""
        raw = make_raw(WATCH_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "watch"

    def test_extracts_action_code(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["action_code"] == 0x07

    def test_extracts_status_flags(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["status_flags"] == 0x03

    def test_extracts_auth_tag(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["auth_tag"] == "a1b2c3"

    def test_identifier_hash_format(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_and_auth_tag(self, parser):
        """Identity = SHA256(mac:auth_tag_hex)[:16]."""
        raw = make_raw(NEARBY_INFO_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)

        expected = hashlib.sha256(
            "AA:BB:CC:DD:EE:FF:a1b2c3".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_action_name_known(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["action_name"] == "Active User (screen on)"

    def test_action_name_watch(self, parser):
        raw = make_raw(WATCH_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["action_name"] == "Watch on wrist/unlocked"

    def test_action_name_unknown(self, parser):
        data = bytearray(NEARBY_INFO_PAYLOAD)
        data[4] = 0x3F  # status_flags=0x3, action_code=0xF (unknown)
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["action_name"] == "Unknown (0x0F)"

    def test_status_details(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)
        details = result.metadata["status_details"]

        # status_flags=0x03: bits 0 and 1 set
        assert details["airpods_connected"] is True
        assert details["wifi_on"] is True
        assert details["primary_icloud"] is False
        assert details["auth_tag_type"] is False

    def test_status_details_all_set(self, parser):
        data = bytearray(NEARBY_INFO_PAYLOAD)
        data[4] = 0xF7  # status_flags=0xF, action_code=0x7
        raw = make_raw(bytes(data))
        result = parser.parse(raw)
        details = result.metadata["status_details"]

        assert details["airpods_connected"] is True
        assert details["wifi_on"] is True
        assert details["primary_icloud"] is True
        assert details["auth_tag_type"] is True

    def test_ios_version(self, parser):
        raw = make_raw(NEARBY_INFO_PAYLOAD)
        result = parser.parse(raw)

        # Byte index 1 of TLV value = 0x18
        assert result.metadata["ios_version"] == 0x18


class TestHandoff:
    def test_parse_valid_handoff(self, parser):
        raw = make_raw(HANDOFF_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_beacon_type_handoff(self, parser):
        raw = make_raw(HANDOFF_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_handoff"

    def test_identifier_hash_format(self, parser):
        raw = make_raw(HANDOFF_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_clipboard_present(self, parser):
        raw = make_raw(HANDOFF_CLIPBOARD_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["clipboard_status"] == "present"

    def test_clipboard_none(self, parser):
        raw = make_raw(HANDOFF_NO_CLIPBOARD_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["clipboard_status"] == "none"

    def test_clipboard_unknown(self, parser):
        data = bytearray(HANDOFF_CLIPBOARD_PAYLOAD)
        data[4] = 0x05  # unknown clipboard status
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["clipboard_status"] == "unknown"

    def test_sequence_number(self, parser):
        raw = make_raw(HANDOFF_CLIPBOARD_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["sequence_number"] == 0x42

    def test_old_handoff_no_sequence(self, parser):
        """Original HANDOFF_PAYLOAD has data but sequence_number should still be extracted."""
        raw = make_raw(HANDOFF_PAYLOAD)
        result = parser.parse(raw)

        # byte[1] of tlv_value = 0x02
        assert result.metadata["sequence_number"] == 0x02


class TestHomeKit:
    def test_beacon_type(self, parser):
        raw = make_raw(HOMEKIT_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_homekit"

    def test_device_class(self, parser):
        raw = make_raw(HOMEKIT_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "iot"

    def test_metadata(self, parser):
        raw = make_raw(HOMEKIT_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["category"] == 0x02
        assert result.metadata["state"] == 0x01
        assert result.metadata["config_number"] == 0x05

    def test_parser_name(self, parser):
        raw = make_raw(HOMEKIT_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_continuity"


class TestHeySiri:
    def test_beacon_type(self, parser):
        raw = make_raw(HEY_SIRI_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_siri"

    def test_device_class(self, parser):
        raw = make_raw(HEY_SIRI_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_metadata(self, parser):
        raw = make_raw(HEY_SIRI_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["perceptual_hash"] == 0x1234
        assert result.metadata["snr"] == 0x0A
        assert result.metadata["confidence"] == 0x63


class TestMagicSwitch:
    def test_beacon_type(self, parser):
        raw = make_raw(MAGIC_SWITCH_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_magic_switch"

    def test_device_class(self, parser):
        raw = make_raw(MAGIC_SWITCH_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_metadata(self, parser):
        raw = make_raw(MAGIC_SWITCH_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["data"] == "aabbcc"


class TestTetheringTarget:
    def test_beacon_type(self, parser):
        raw = make_raw(TETHERING_TARGET_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_tethering"

    def test_device_class(self, parser):
        raw = make_raw(TETHERING_TARGET_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_metadata(self, parser):
        raw = make_raw(TETHERING_TARGET_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["signal_strength"] == 0xC8
        assert result.metadata["battery"] == 0x4B


class TestTetheringSource:
    def test_beacon_type(self, parser):
        raw = make_raw(TETHERING_SOURCE_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_tethering_source"

    def test_device_class(self, parser):
        raw = make_raw(TETHERING_SOURCE_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_metadata(self, parser):
        raw = make_raw(TETHERING_SOURCE_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["signal_strength"] == 0xD0
        assert result.metadata["battery"] == 0x32


class TestTetheringSourceType0x16:
    """TLV type 0x16 — a different Tethering Source variant."""

    TETHERING_SRC_0x16_PAYLOAD = bytes([
        0x4C, 0x00,  # Apple company ID
        0x16,        # Type: Tethering Source (alternate)
        0x02,        # Length: 2
        0xB0,        # signal_strength
        0x50,        # battery
    ])

    def test_parse_succeeds(self, parser):
        raw = make_raw(self.TETHERING_SRC_0x16_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None

    def test_beacon_type(self, parser):
        raw = make_raw(self.TETHERING_SRC_0x16_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "apple_tethering_source"


class TestOverflowAreaType0x01:
    """TLV type 0x01 — Overflow Area."""

    OVERFLOW_AREA_PAYLOAD = bytes([
        0x4C, 0x00,  # Apple company ID
        0x01,        # Type: Overflow Area
        0x04,        # Length: 4
        0xAA, 0xBB, 0xCC, 0xDD,
    ])

    def test_parse_succeeds(self, parser):
        raw = make_raw(self.OVERFLOW_AREA_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(self.OVERFLOW_AREA_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_continuity"


class TestHeySiriVariant0x0A:
    """TLV type 0x0A — Hey Siri variant (NOT same as existing 0x08)."""

    HEY_SIRI_0x0A_PAYLOAD = bytes([
        0x4C, 0x00,  # Apple company ID
        0x0A,        # Type: Hey Siri variant
        0x04,        # Length: 4
        0x56, 0x78,  # perceptual_hash
        0x0C,        # snr
        0x80,        # confidence
    ])

    def test_parse_succeeds(self, parser):
        raw = make_raw(self.HEY_SIRI_0x0A_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None

    def test_beacon_type(self, parser):
        raw = make_raw(self.HEY_SIRI_0x0A_PAYLOAD)
        result = parser.parse(raw)

        assert "siri" in result.beacon_type


class TestMalformed:
    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(NEARBY_INFO_PAYLOAD)
        data[0] = 0x06
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_non_matching_tlv_type(self, parser):
        """TLV type that's not a known continuity type should return None."""
        data = bytearray(NEARBY_INFO_PAYLOAD)
        data[2] = 0x02  # iBeacon subtype, not continuity
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        raw = make_raw(bytes([0x4C, 0x00, 0x10]))
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_empty_manufacturer_data(self, parser):
        raw = make_raw(b"")
        assert parser.parse(raw) is None
