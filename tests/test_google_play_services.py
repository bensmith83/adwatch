"""Tests for Google Play Services BLE presence plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.google_play_services import GooglePlayServicesParser


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


class TestGooglePlayServicesParser:
    def _register(self, registry):
        @register_parser(
            name="google_play_services",
            service_uuid="fcf1",
            description="Google Play Services (Android)",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(GooglePlayServicesParser):
            pass
        return TestParser

    def test_match_by_service_uuid_in_service_uuids(self):
        """Should match when fcf1 is in service_uuids."""
        registry = ParserRegistry()
        self._register(registry)

        ad = _make_ad(service_uuids=["fcf1"])
        assert len(registry.match(ad)) == 1

    def test_match_by_service_uuid_in_service_data(self):
        """Should match when fcf1 is a key in service_data."""
        registry = ParserRegistry()
        self._register(registry)

        ad = _make_ad(service_data={"fcf1": b"\x01\x02"})
        assert len(registry.match(ad)) == 1

    def test_beacon_type_and_device_class(self):
        """Should return correct beacon_type and device_class."""
        registry = ParserRegistry()
        self._register(registry)

        ad = _make_ad(service_uuids=["fcf1"])
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.beacon_type == "google_play_services"
        assert result.device_class == "phone"

    def test_returns_none_when_no_matching_uuid(self):
        """Should return None when no fcf1 UUID present."""
        registry = ParserRegistry()
        self._register(registry)

        ad = _make_ad(service_uuids=["abcd"])
        # Registry won't match, but test parse directly
        parser = GooglePlayServicesParser()
        assert parser.parse(ad) is None

    def test_service_data_hex_in_raw_payload(self):
        """Should include service data hex in raw_payload_hex."""
        registry = ParserRegistry()
        self._register(registry)

        ad = _make_ad(service_data={"fcf1": b"\xde\xad"})
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.raw_payload_hex == "dead"

    def test_identity_hash_based_on_mac(self):
        """Identity hash: SHA256('{mac}:google_play_services')[:16]."""
        registry = ParserRegistry()
        self._register(registry)

        ad = _make_ad(service_uuids=["fcf1"], mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256(
            "11:22:33:44:55:66:google_play_services".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected
