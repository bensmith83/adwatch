"""Tests for Google Chromecast/Home BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.google_chromecast import GoogleChromecastParser, CHROMECAST_SERVICE_UUID


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
        name="google_chromecast",
        service_uuid=CHROMECAST_SERVICE_UUID,
        description="Google Chromecast/Home advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GoogleChromecastParser):
        pass

    return registry


class TestGoogleChromecastParser:
    # --- Registry matching ---

    def test_matches_service_uuid_fe2c(self):
        """Matches on service_uuid fe2c in service_data."""
        registry = _make_registry()
        ad = _make_ad(service_data={"fe2c": b"\x00\x30\x00\x00\x00"})
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_service_uuid_constant(self):
        """CHROMECAST_SERVICE_UUID is 'fe2c'."""
        assert CHROMECAST_SERVICE_UUID == "fe2c"

    # --- Basic fields ---

    def test_parser_name(self):
        """parser_name is 'google_chromecast'."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"fe2c": b"\x00\x30\x00\x00\x00"})
        result = parser.parse(ad)
        assert result.parser_name == "google_chromecast"

    def test_beacon_type(self):
        """beacon_type is 'google_chromecast'."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"fe2c": b"\x00\x30\x00\x00\x00"})
        result = parser.parse(ad)
        assert result.beacon_type == "google_chromecast"

    def test_device_class(self):
        """device_class is 'media'."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"fe2c": b"\x00\x30\x00\x00\x00"})
        result = parser.parse(ad)
        assert result.device_class == "media"

    # --- Service data parsing (full 12-byte payload) ---

    def test_version_byte(self):
        """metadata['version'] is byte 0 of service data."""
        parser = GoogleChromecastParser()
        data = b"\x00\x30\x00\x00\x00\x21\x6f\x56\x34\x7f\xe4\xd2"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.metadata["version"] == 0

    def test_device_type_byte(self):
        """metadata['device_type'] is byte 1 of service data."""
        parser = GoogleChromecastParser()
        data = b"\x00\x30\x00\x00\x00\x21\x6f\x56\x34\x7f\xe4\xd2"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.metadata["device_type"] == 0x30

    def test_device_type_name_chromecast(self):
        """device_type 0x30 -> device_type_name='Chromecast'."""
        parser = GoogleChromecastParser()
        data = b"\x00\x30\x00\x00\x00\x21\x6f\x56\x34\x7f\xe4\xd2"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.metadata["device_type_name"] == "Chromecast"

    def test_flags_hex(self):
        """metadata['flags_hex'] is hex of bytes 2-4."""
        parser = GoogleChromecastParser()
        data = b"\x00\x30\xAB\xCD\xEF\x21\x6f\x56\x34\x7f\xe4\xd2"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.metadata["flags_hex"] == "abcdef"

    def test_device_id_hex(self):
        """metadata['device_id_hex'] is hex of bytes 5-8."""
        parser = GoogleChromecastParser()
        data = b"\x00\x30\x00\x00\x00\x21\x6f\x56\x34\x7f\xe4\xd2"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.metadata["device_id_hex"] == "216f5634"

    # --- Non-Chromecast device type ---

    def test_device_type_name_google_home(self):
        """device_type != 0x30 -> device_type_name='Google Home'."""
        parser = GoogleChromecastParser()
        data = b"\x00\x01\x00\x00\x00\x21\x6f\x56\x34\x7f\xe4\xd2"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.metadata["device_type_name"] == "Google Home"

    # --- Short service data ---

    def test_short_service_data(self):
        """Short service data (<5 bytes) still returns a result."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"fe2c": b"\x00\x30"})
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "google_chromecast"

    def test_short_service_data_missing_fields(self):
        """Short service data has version/device_type but no flags/device_id."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"fe2c": b"\x00\x30"})
        result = parser.parse(ad)
        assert result.metadata.get("version") == 0
        assert result.metadata.get("device_type") == 0x30
        assert "device_id_hex" not in result.metadata

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:google_chromecast)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = GoogleChromecastParser()
        ad = _make_ad(
            service_data={"fe2c": b"\x00\x30\x00\x00\x00"},
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:google_chromecast".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex(self):
        """raw_payload_hex is hex of the fe2c service data bytes."""
        parser = GoogleChromecastParser()
        data = b"\x00\x30\xAB\xCD\xEF"
        ad = _make_ad(service_data={"fe2c": data})
        result = parser.parse(ad)
        assert result.raw_payload_hex == data.hex()

    # --- No service data but UUID in service_uuids ---

    def test_service_uuids_fallback(self):
        """service_data=None but full UUID in service_uuids -> basic result."""
        parser = GoogleChromecastParser()
        ad = _make_ad(
            service_data=None,
            service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "google_chromecast"
        assert result.raw_payload_hex == ""

    # --- Edge cases ---

    def test_returns_none_no_service_data_no_uuids(self):
        """Returns None for no service_data and no matching service_uuids."""
        parser = GoogleChromecastParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_different_uuid(self):
        """Returns None for service_data with different UUID only."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"feaf": b"\x00\x30\x00\x00\x00"})
        result = parser.parse(ad)
        assert result is None

    def test_empty_service_data_bytes(self):
        """Empty service data bytes (b'') -> returns basic result."""
        parser = GoogleChromecastParser()
        ad = _make_ad(service_data={"fe2c": b""})
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "google_chromecast"
        assert result.raw_payload_hex == ""

    def test_rejects_uuid_with_fe2c_substring_that_is_not_chromecast(self):
        """A UUID containing 'fe2c' as substring but NOT the Chromecast UUID must be rejected."""
        parser = GoogleChromecastParser()
        ad = _make_ad(
            service_data=None,
            service_uuids=["abcfe2cd-1234-5678-9abc-def012345678"],
        )
        result = parser.parse(ad)
        assert result is None, (
            "Parser should not match a UUID that merely contains 'fe2c' as a substring"
        )

    def test_matches_full_chromecast_uuid(self):
        """The full-form Chromecast UUID 0000fe2c-... must still match."""
        parser = GoogleChromecastParser()
        ad = _make_ad(
            service_data=None,
            service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "google_chromecast"
