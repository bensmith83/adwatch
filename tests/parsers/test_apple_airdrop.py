"""Tests for Apple AirDrop parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.apple_airdrop import AppleAirDropParser


@pytest.fixture
def parser():
    return AppleAirDropParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# AirDrop: 4c 00 05 08 a1 b2 c3 d4 e5 f6 00 00
AIRDROP_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x05,        # Type: AirDrop
    0x08,        # Length: 8
    0xA1, 0xB2,  # AppleID hash
    0xC3, 0xD4,  # Phone hash
    0xE5, 0xF6,  # Email hash
    0x00, 0x00,  # Email2 hash (not set)
])


class TestAppleAirDropParser:
    def test_parse_valid_airdrop(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_airdrop"

    def test_device_class_phone(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "phone"

    def test_extracts_appleid_hash(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["appleid_hash"] == "a1b2"

    def test_extracts_phone_hash(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["phone_hash"] == "c3d4"

    def test_extracts_email_hash(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["email_hash"] == "e5f6"

    def test_extracts_email2_hash(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["email2_hash"] == "0000"

    def test_identifier_hash_format(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_based_on_combined_hashes(self, parser):
        """Identity = SHA256(combined_hashes)[:16]."""
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        combined = "a1b2c3d4e5f60000"
        expected = hashlib.sha256(combined.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(AIRDROP_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_tlv_type(self, parser):
        data = bytearray(AIRDROP_PAYLOAD)
        data[2] = 0x10
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        # Less than 8 bytes in TLV value
        raw = make_raw(bytes([0x4C, 0x00, 0x05, 0x04, 0xA1, 0xB2, 0xC3, 0xD4]))
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(AIRDROP_PAYLOAD)
        data[0] = 0x06
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None
