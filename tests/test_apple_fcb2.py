"""Tests for Apple FCB2 presence plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.apple_fcb2 import AppleFCB2Parser, APPLE_FCB2_UUID


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "service_uuids": None,
        "local_name": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


@pytest.fixture
def registry():
    return ParserRegistry()


@pytest.fixture
def parser(registry):
    return AppleFCB2Parser()


class TestAppleFCB2Match:
    """Test UUID matching logic."""

    def test_matches_service_uuid_in_service_uuids(self, parser):
        ad = _make_ad(service_uuids=["fcb2"])
        result = parser.parse(ad)
        assert result is not None
        assert result.beacon_type == "apple_fcb2"

    def test_matches_service_uuid_in_service_data(self, parser):
        ad = _make_ad(service_data={"fcb2": b"\x01\x02"})
        result = parser.parse(ad)
        assert result is not None
        assert result.beacon_type == "apple_fcb2"

    def test_returns_none_no_matching_uuid(self, parser):
        ad = _make_ad(service_uuids=["abcd"], service_data={"1234": b"\x00"})
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_empty_ad(self, parser):
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None


class TestAppleFCB2ParseResult:
    """Test parse result fields."""

    def test_beacon_type_and_device_class(self, parser):
        ad = _make_ad(service_uuids=["fcb2"])
        result = parser.parse(ad)
        assert result.beacon_type == "apple_fcb2"
        assert result.device_class == "phone"
        assert result.parser_name == "apple_fcb2"

    def test_service_data_hex_in_payload(self, parser):
        payload = b"\xaa\xbb\xcc"
        ad = _make_ad(service_data={"fcb2": payload})
        result = parser.parse(ad)
        assert result.raw_payload_hex == "aabbcc"

    def test_empty_payload_when_uuid_only(self, parser):
        ad = _make_ad(service_uuids=["fcb2"])
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_identity_hash_based_on_mac(self, parser):
        mac = "11:22:33:44:55:66"
        ad = _make_ad(mac_address=mac, service_uuids=["fcb2"])
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:apple_fcb2".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_metadata_contains_service_name(self, parser):
        ad = _make_ad(service_uuids=["fcb2"])
        result = parser.parse(ad)
        assert "service" in result.metadata
        assert "FCB2" in result.metadata["service"]
