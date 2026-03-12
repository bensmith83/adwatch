"""Tests for Apple Find My parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.apple_findmy import AppleFindMyParser


@pytest.fixture
def parser():
    return AppleFindMyParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# Find My: TLV type 0x12 with 28-byte EC key fragment
FINDMY_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x12,        # Type: Find My
    0x1C,        # Length: 28
]) + bytes(range(0x01, 0x1D))  # 28 bytes of EC key fragment


class TestAppleFindMyParser:
    def test_parse_valid_findmy(self, parser):
        raw = make_raw(FINDMY_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(FINDMY_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_findmy"

    def test_device_class_tracker(self, parser):
        raw = make_raw(FINDMY_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "tracker"

    def test_extracts_ec_key_fragment(self, parser):
        """Should extract EC public key fragment from payload."""
        raw = make_raw(FINDMY_PAYLOAD)
        result = parser.parse(raw)

        # The EC key fragment is the TLV value (28 bytes)
        assert "public_key" in result.metadata or "ec_key_fragment" in result.metadata

    def test_identifier_hash_format(self, parser):
        raw = make_raw(FINDMY_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_and_key_fragment(self, parser):
        """Identity = SHA256(mac:ec_key_hex)[:16], excluding status byte."""
        raw = make_raw(FINDMY_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)

        # EC key fragment is bytes 1+ of TLV value (byte 0 is status)
        ec_key_hex = bytes(range(0x02, 0x1D)).hex()
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{ec_key_hex}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(FINDMY_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_tlv_type(self, parser):
        data = bytearray(FINDMY_PAYLOAD)
        data[2] = 0x10  # Nearby Info, not Find My
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        # Only company ID + type, no length/value
        raw = make_raw(bytes([0x4C, 0x00, 0x12]))
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(FINDMY_PAYLOAD)
        data[0] = 0x06
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_minimum_length_payload(self, parser):
        """Minimum length for Find My is 2 bytes per doc."""
        minimal = bytes([0x4C, 0x00, 0x12, 0x02, 0xAA, 0xBB])
        raw = make_raw(minimal)
        result = parser.parse(raw)

        assert result is not None


class TestFindMyStatusByte:
    """Tests for status byte decoding (byte 0 of TLV value)."""

    def _make_findmy(self, status_byte, key_len=27):
        """Build a Find My payload with a specific status byte."""
        tlv_len = 1 + key_len  # status byte + key fragment
        payload = bytes([0x4C, 0x00, 0x12, tlv_len, status_byte])
        payload += bytes(range(0xA0, 0xA0 + key_len))
        return payload

    @pytest.fixture
    def parser(self):
        return AppleFindMyParser()

    def test_ec_key_fragment_excludes_status_byte(self, parser):
        """ec_key_fragment should be bytes 1+ of TLV value, not byte 0."""
        status_byte = 0x14
        key_bytes = bytes(range(0xA0, 0xA0 + 27))
        payload = self._make_findmy(status_byte)
        raw = make_raw(payload)
        result = parser.parse(raw)

        assert result.metadata["ec_key_fragment"] == key_bytes.hex()

    def test_battery_full(self, parser):
        raw = make_raw(self._make_findmy(0x14))  # 0x1_ = full
        result = parser.parse(raw)
        assert result.metadata["battery_status"] == "full"

    def test_battery_medium(self, parser):
        raw = make_raw(self._make_findmy(0x50))  # 0x5_ = medium
        result = parser.parse(raw)
        assert result.metadata["battery_status"] == "medium"

    def test_battery_low(self, parser):
        raw = make_raw(self._make_findmy(0x90))  # 0x9_ = low
        result = parser.parse(raw)
        assert result.metadata["battery_status"] == "low"

    def test_battery_critical(self, parser):
        raw = make_raw(self._make_findmy(0xD0))  # 0xD_ = critical
        result = parser.parse(raw)
        assert result.metadata["battery_status"] == "critical"

    def test_battery_unknown_nibble(self, parser):
        raw = make_raw(self._make_findmy(0x00))  # 0x0_ = unknown
        result = parser.parse(raw)
        assert result.metadata["battery_status"] == "unknown"

    def test_device_type_airtag(self, parser):
        raw = make_raw(self._make_findmy(0x10))  # bits 3-2 = 0b00
        result = parser.parse(raw)
        assert result.metadata["findmy_device_type"] == "airtag"
        assert result.device_class == "tracker"

    def test_device_type_apple_device(self, parser):
        raw = make_raw(self._make_findmy(0x14))  # bits 3-2 = 0b01
        result = parser.parse(raw)
        assert result.metadata["findmy_device_type"] == "apple_device"
        assert result.device_class == "phone"

    def test_device_type_airpods(self, parser):
        raw = make_raw(self._make_findmy(0x18))  # bits 3-2 = 0b10
        result = parser.parse(raw)
        assert result.metadata["findmy_device_type"] == "airpods"
        assert result.device_class == "accessory"

    def test_device_type_third_party(self, parser):
        raw = make_raw(self._make_findmy(0x1C))  # bits 3-2 = 0b11
        result = parser.parse(raw)
        assert result.metadata["findmy_device_type"] == "third_party"
        assert result.device_class == "tracker"

    def test_separated_false(self, parser):
        raw = make_raw(self._make_findmy(0x10))  # bit 1 = 0
        result = parser.parse(raw)
        assert result.metadata["separated"] is False

    def test_separated_true(self, parser):
        raw = make_raw(self._make_findmy(0x12))  # bit 1 = 1
        result = parser.parse(raw)
        assert result.metadata["separated"] is True

    def test_combined_status_byte(self, parser):
        """0x9A = low battery, airpods, separated."""
        raw = make_raw(self._make_findmy(0x9A))
        result = parser.parse(raw)
        assert result.metadata["battery_status"] == "low"
        assert result.metadata["findmy_device_type"] == "airpods"
        assert result.metadata["separated"] is True
        assert result.device_class == "accessory"
