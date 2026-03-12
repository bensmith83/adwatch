"""Tests for Apple Nearby Action parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.apple_nearby_action import AppleNearbyActionParser


@pytest.fixture
def parser():
    return AppleNearbyActionParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# WiFi Password sharing: 4c 00 0f 03 40 09 00
WIFI_PASSWORD_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x0F,        # Type: Nearby Action
    0x03,        # Length: 3
    0x40,        # Action Flags
    0x09,        # Action Type: WiFi Password
    0x00,        # Action-specific data
])

# Apple Pay: 4c 00 0f 02 00 0e
APPLE_PAY_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x0F,        # Type: Nearby Action
    0x02,        # Length: 2
    0x00,        # Action Flags
    0x0E,        # Action Type: Apple Pay
])


class TestAppleNearbyActionParser:
    def test_parse_valid_nearby_action(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_nearby_action"

    def test_device_class_phone(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_extracts_action_type_wifi(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["action_type"] == 0x09

    def test_extracts_action_type_apple_pay(self, parser):
        raw = make_raw(APPLE_PAY_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["action_type"] == 0x0E

    def test_extracts_action_flags(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["action_flags"] == 0x40

    def test_identifier_hash_format(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_and_payload(self, parser):
        """Identity = SHA256(mac:payload_hex)[:16]."""
        raw = make_raw(WIFI_PASSWORD_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)

        payload_hex = bytes([0x40, 0x09, 0x00]).hex()
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{payload_hex}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(WIFI_PASSWORD_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_tlv_type(self, parser):
        data = bytearray(WIFI_PASSWORD_PAYLOAD)
        data[2] = 0x10
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        # Less than minimum 2 bytes in TLV value
        raw = make_raw(bytes([0x4C, 0x00, 0x0F, 0x01, 0x40]))
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(WIFI_PASSWORD_PAYLOAD)
        data[0] = 0x06
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    # --- Action type name lookup ---

    @pytest.mark.parametrize(
        "action_type, expected_name",
        [
            (0x01, "Apple TV Setup"),
            (0x04, "Mobile Backup"),
            (0x05, "Watch Setup"),
            (0x06, "Apple TV Pair"),
            (0x07, "Internet Relay"),
            (0x08, "WiFi Password Sharing"),
            (0x09, "iOS Setup / Homekit"),
            (0x0A, "Repair"),
            (0x0B, "Speaker Setup"),
            (0x0C, "Apple Pay"),
            (0x0D, "Whole Home Audio Setup"),
            (0x0E, "Developer Tools Pairing"),
            (0x0F, "Answered Call"),
            (0x10, "Ended Call"),
            (0x13, "Handoff (Safari)"),
            (0x14, "Handoff (Keynote)"),
            (0x27, "Apple TV Connect"),
        ],
    )
    def test_action_type_name_lookup(self, parser, action_type, expected_name):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x00, action_type])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["action_type_name"] == expected_name

    def test_action_type_name_unknown(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x00, 0xFF])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["action_type_name"] == "Unknown (0xff)"

    # --- Action flags decomposition ---

    def test_auth_tag_present_flag_set(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x01, 0x09])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["auth_tag_present"] is True

    def test_auth_tag_present_flag_unset(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x00, 0x09])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["auth_tag_present"] is False

    def test_is_sender_flag_set(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x02, 0x09])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["is_sender"] is True

    def test_is_sender_flag_unset(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x00, 0x09])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["is_sender"] is False

    def test_both_flags_set(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x03, 0x09])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["auth_tag_present"] is True
        assert result.metadata["is_sender"] is True

    # --- WiFi Password Sharing SSID hash ---

    def test_wifi_password_ssid_hash(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x05, 0x40, 0x08, 0xAB, 0xCD, 0xEF])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["ssid_hash_hex"] == "abcdef"

    def test_wifi_password_no_ssid_hash_when_no_extra_bytes(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x02, 0x40, 0x08])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert "ssid_hash_hex" not in result.metadata

    def test_non_wifi_action_no_ssid_hash(self, parser):
        payload = bytes([0x4C, 0x00, 0x0F, 0x05, 0x00, 0x01, 0xAB, 0xCD, 0xEF])
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert "ssid_hash_hex" not in result.metadata
