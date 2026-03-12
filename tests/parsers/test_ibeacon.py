"""Tests for iBeacon parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.ibeacon import IBeaconParser


@pytest.fixture
def parser():
    return IBeaconParser()


def make_raw(manufacturer_data, **kwargs):
    """Create a RawAdvertisement with given manufacturer_data."""
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# Canonical iBeacon: UUID=2f234454-cf6d-4a0f-adf2-f4911ba9ffa6, Major=1, Minor=42, TX=-59
IBEACON_PAYLOAD = bytes([
    0x4C, 0x00,  # Company ID (Apple, little-endian)
    0x02,        # Subtype: iBeacon
    0x15,        # Length: 21 bytes
    # UUID: 2f234454-cf6d-4a0f-adf2-f4911ba9ffa6
    0x2F, 0x23, 0x44, 0x54, 0xCF, 0x6D, 0x4A, 0x0F,
    0xAD, 0xF2, 0xF4, 0x91, 0x1B, 0xA9, 0xFF, 0xA6,
    0x00, 0x01,  # Major = 1
    0x00, 0x2A,  # Minor = 42
    0xC5,        # TX Power = -59 dBm (signed)
])

EXPECTED_UUID = "2f234454-cf6d-4a0f-adf2-f4911ba9ffa6"


class TestIBeaconParser:
    def test_parse_valid_ibeacon(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "ibeacon"

    def test_beacon_type(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.beacon_type == "ibeacon"

    def test_device_class(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "beacon"

    def test_extracts_uuid(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["uuid"] == EXPECTED_UUID

    def test_extracts_major(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["major"] == 1

    def test_extracts_minor(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["minor"] == 42

    def test_extracts_tx_power(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        # 0xC5 = 197 unsigned, -59 signed
        assert result.metadata["tx_power"] == -59

    def test_identifier_hash_format(self, parser):
        """identifier_hash should be a 16-char hex string."""
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # should not raise

    def test_identifier_hash_based_on_uuid_major_minor(self, parser):
        """Identity = SHA256(UUID:Major:Minor)[:16]."""
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        expected = hashlib.sha256(
            f"{EXPECTED_UUID}:1:42".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identifier_hash_stable_across_macs(self, parser):
        """iBeacon identity doesn't depend on MAC."""
        raw1 = make_raw(IBEACON_PAYLOAD, mac_address="11:22:33:44:55:66")
        raw2 = make_raw(IBEACON_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")

        result1 = parser.parse(raw1)
        result2 = parser.parse(raw2)

        assert result1.identifier_hash == result2.identifier_hash

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(IBEACON_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_company_id(self, parser):
        """Non-Apple company ID should return None."""
        data = bytearray(IBEACON_PAYLOAD)
        data[0] = 0x06  # Microsoft instead of Apple
        data[1] = 0x00
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_subtype(self, parser):
        """Non-iBeacon subtype should return None."""
        data = bytearray(IBEACON_PAYLOAD)
        data[2] = 0x10  # Nearby Info instead of iBeacon
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_length_byte(self, parser):
        """Wrong length byte (not 0x15) should return None."""
        data = bytearray(IBEACON_PAYLOAD)
        data[3] = 0x10  # Wrong length
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        """Truncated payload should return None."""
        raw = make_raw(IBEACON_PAYLOAD[:10])
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_empty_manufacturer_data(self, parser):
        raw = make_raw(b"")
        assert parser.parse(raw) is None

    def test_different_uuid_major_minor(self, parser):
        """Verify parsing works with different values."""
        data = bytearray(IBEACON_PAYLOAD)
        # Set Major=256 (0x0100), Minor=1000 (0x03E8)
        data[20] = 0x01
        data[21] = 0x00
        data[22] = 0x03
        data[23] = 0xE8
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["major"] == 256
        assert result.metadata["minor"] == 1000


class TestIBeaconBigEndianCompanyId:
    """Test iBeacon ads with big-endian company ID (0x004c as bytes 00 4c)."""

    # Real-world observed payload: company ID in big-endian byte order
    # 004c02152686f39cbada4658854aa62e7e5e8b8d00010000c9
    BIG_ENDIAN_PAYLOAD = bytes.fromhex(
        "004c02152686f39cbada4658854aa62e7e5e8b8d00010000c9"
    )
    EXPECTED_UUID = "2686f39c-bada-4658-854a-a62e7e5e8b8d"

    def test_parse_succeeds(self, parser):
        """Big-endian company ID 004c should still be recognized as Apple."""
        raw = make_raw(self.BIG_ENDIAN_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_uuid(self, parser):
        raw = make_raw(self.BIG_ENDIAN_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["uuid"] == self.EXPECTED_UUID

    def test_major(self, parser):
        raw = make_raw(self.BIG_ENDIAN_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["major"] == 1

    def test_minor(self, parser):
        raw = make_raw(self.BIG_ENDIAN_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["minor"] == 0

    def test_tx_power(self, parser):
        raw = make_raw(self.BIG_ENDIAN_PAYLOAD)
        result = parser.parse(raw)

        # 0xC9 = -55 signed
        assert result.metadata["tx_power"] == -55
