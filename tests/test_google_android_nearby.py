"""Tests for Google Android Nearby BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.google_android_nearby import GoogleAndroidNearbyParser, FRAME_TYPES


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="google_android_nearby",
        service_uuid="fef3",
        description="Google Android Nearby sharing advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GoogleAndroidNearbyParser):
        pass

    return registry


class TestGoogleAndroidNearbyParser:
    def test_matches_service_uuid(self):
        """Matches on service_uuid fef3."""
        registry = _make_registry()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17\x00\x00"})
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_without_service_data(self):
        """Does not match when no service_data present."""
        registry = _make_registry()
        ad = _make_ad()
        matches = registry.match(ad)
        assert len(matches) == 0

    def test_parse_long_frame_type(self):
        """Parses magic 0x4a17 as 'long' frame type."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17\x00\x00"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "long"
        assert result.metadata["magic"] == "4a17"

    def test_parse_short_frame_type(self):
        """Parses magic 0x1101 as 'short' frame type."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x11\x01\xAB\xCD"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "short"
        assert result.metadata["magic"] == "1101"

    def test_parse_short_extended_frame_type(self):
        """Parses magic 0x1102 as 'short_extended' frame type."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x11\x02\xFF"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "short_extended"
        assert result.metadata["magic"] == "1102"

    def test_parse_unknown_frame_type(self):
        """Unknown magic bytes result in 'unknown' frame type."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\xFF\xFF\x00"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "unknown"
        assert result.metadata["magic"] == "ffff"

    def test_returns_none_no_service_data(self):
        """Returns None when service_data is None."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_missing_fef3_key(self):
        """Returns None when fef3 key not in service_data."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"abcd": b"\x00\x00"})
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_data(self):
        """Returns None when service data is less than 2 bytes."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a"})
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_empty_data(self):
        """Returns None when service data is empty."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b""})
        result = parser.parse(ad)
        assert result is None

    def test_device_class(self):
        """device_class is always 'phone'."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17\x00"})
        result = parser.parse(ad)
        assert result.device_class == "phone"

    def test_beacon_type(self):
        """beacon_type is 'google_android_nearby'."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17\x00"})
        result = parser.parse(ad)
        assert result.beacon_type == "google_android_nearby"

    def test_parser_name(self):
        """parser_name is 'google_android_nearby'."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17\x00"})
        result = parser.parse(ad)
        assert result.parser_name == "google_android_nearby"

    def test_identity_hash_format(self):
        """Identity hash is SHA256('google_android_nearby:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17\x00"}, mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"google_android_nearby:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_different_macs(self):
        """Different MAC addresses produce different identity hashes."""
        parser = GoogleAndroidNearbyParser()
        ad1 = _make_ad(service_data={"fef3": b"\x4a\x17"}, mac_address="AA:BB:CC:DD:EE:01")
        ad2 = _make_ad(service_data={"fef3": b"\x4a\x17"}, mac_address="AA:BB:CC:DD:EE:02")
        r1 = parser.parse(ad1)
        r2 = parser.parse(ad2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_raw_payload_hex(self):
        """raw_payload_hex contains service data as hex."""
        parser = GoogleAndroidNearbyParser()
        data = b"\x4a\x17\xAB\xCD\xEF"
        ad = _make_ad(service_data={"fef3": data})
        result = parser.parse(ad)
        assert result.raw_payload_hex == data.hex()

    def test_data_length_in_metadata(self):
        """data_length in metadata reflects actual data size."""
        parser = GoogleAndroidNearbyParser()
        data = b"\x11\x01\x00\x01\x02\x03"
        ad = _make_ad(service_data={"fef3": data})
        result = parser.parse(ad)
        assert result.metadata["data_length"] == 6

    def test_hex_string_service_data(self):
        """Handles service data passed as hex string instead of bytes."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": "4a170000"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "long"
        assert result.metadata["magic"] == "4a17"

    def test_hex_string_short_data(self):
        """Returns None for hex string data that's less than 2 bytes."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": "4a"})
        result = parser.parse(ad)
        assert result is None

    def test_minimum_valid_data(self):
        """Exactly 2 bytes of data is valid (minimum)."""
        parser = GoogleAndroidNearbyParser()
        ad = _make_ad(service_data={"fef3": b"\x4a\x17"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["data_length"] == 2

    def test_all_known_frame_types(self):
        """All entries in FRAME_TYPES constant are parseable."""
        parser = GoogleAndroidNearbyParser()
        for magic_int, expected_type in FRAME_TYPES.items():
            data = magic_int.to_bytes(2, "big") + b"\x00"
            ad = _make_ad(service_data={"fef3": data})
            result = parser.parse(ad)
            assert result is not None
            assert result.metadata["frame_type"] == expected_type

    def test_via_registry_parse(self):
        """End-to-end: registry match and parse produces correct result."""
        registry = _make_registry()
        ad = _make_ad(service_data={"fef3": b"\x11\x01\xDE\xAD"})
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "google_android_nearby"
        assert result.metadata["frame_type"] == "short"
