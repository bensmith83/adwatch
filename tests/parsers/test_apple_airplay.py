"""Tests for Apple AirPlay Target parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.apple_airplay import AppleAirPlayParser


@pytest.fixture
def parser():
    return AppleAirPlayParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# AirPlay target with config seed 0x1234, no IPv4
# 4c 00 09 03 80 12 34
AIRPLAY_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x09,        # Type: AirPlay Target
    0x03,        # Length: 3
    0x80,        # Flags
    0x12, 0x34,  # Config Seed (big-endian: 0x1234)
])

# AirPlay target with IPv4 address 192.168.1.50
AIRPLAY_WITH_IP = bytes([
    0x4C, 0x00,  # Apple company ID
    0x09,        # Type: AirPlay Target
    0x0A,        # Length: 10
    0x80,        # Flags
    0x12, 0x34,  # Config Seed
    0x00, 0x00, 0x00,  # Padding
    0xC0, 0xA8, 0x01, 0x32,  # IPv4: 192.168.1.50
])


class TestAppleAirPlayParser:
    def test_parse_valid_airplay(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_airplay"

    def test_device_class_media(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "media"

    def test_extracts_flags(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["flags"] == 0x80

    def test_extracts_config_seed(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["config_seed"] == 0x1234

    def test_extracts_ipv4_when_present(self, parser):
        raw = make_raw(AIRPLAY_WITH_IP)
        result = parser.parse(raw)

        assert result.metadata.get("ipv4") == "192.168.1.50"

    def test_no_ipv4_when_short_payload(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        # Short payload (3 bytes) should not have IPv4
        assert result.metadata.get("ipv4") is None or "ipv4" not in result.metadata

    def test_identifier_hash_format(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_and_payload(self, parser):
        """Identity = SHA256(mac:payload_hex)[:16]."""
        raw = make_raw(AIRPLAY_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)

        payload_hex = bytes([0x80, 0x12, 0x34]).hex()
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{payload_hex}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(AIRPLAY_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_tlv_type(self, parser):
        data = bytearray(AIRPLAY_PAYLOAD)
        data[2] = 0x10
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        # Less than minimum 3 bytes in TLV value
        raw = make_raw(bytes([0x4C, 0x00, 0x09, 0x01, 0x80]))
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(AIRPLAY_PAYLOAD)
        data[0] = 0x06
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None
