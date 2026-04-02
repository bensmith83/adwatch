"""Tests for Razer gaming peripheral BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.razer_ble import RazerBleParser, RAZER_SERVICE_UUID


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
        name="razer",
        service_uuid=RAZER_SERVICE_UUID,
        local_name_pattern=r"^Razer\s",
        description="Razer gaming peripheral advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(RazerBleParser):
        pass

    return registry


class TestRazerBleRegistry:
    def test_matches_service_uuid(self):
        """Matches when service_uuids contains the Razer UUID."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fd65"])
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name 'Razer Lev3' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="Razer Lev3")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestRazerBleParser:
    def test_parser_name(self):
        """parser_name is 'razer'."""
        parser = RazerBleParser()
        ad = _make_ad(local_name="Razer Lev3")
        result = parser.parse(ad)
        assert result.parser_name == "razer"

    def test_beacon_type(self):
        """beacon_type is 'razer'."""
        parser = RazerBleParser()
        ad = _make_ad(local_name="Razer Lev3")
        result = parser.parse(ad)
        assert result.beacon_type == "razer"

    def test_device_class(self):
        """device_class is 'gaming_peripheral'."""
        parser = RazerBleParser()
        ad = _make_ad(local_name="Razer Lev3")
        result = parser.parse(ad)
        assert result.device_class == "gaming_peripheral"

    def test_product_extraction(self):
        """'Razer Lev3' -> metadata['product'] == 'Lev3'."""
        parser = RazerBleParser()
        ad = _make_ad(local_name="Razer Lev3")
        result = parser.parse(ad)
        assert result.metadata["product"] == "Lev3"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'Razer Lev3'."""
        parser = RazerBleParser()
        ad = _make_ad(local_name="Razer Lev3")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Razer Lev3"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:razer)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = RazerBleParser()
        ad = _make_ad(local_name="Razer Lev3", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:razer".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_uuid_match_without_name(self):
        """Parses with service_uuid match even when local_name is None."""
        parser = RazerBleParser()
        ad = _make_ad(service_uuids=["fd65"])
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "razer"
        assert "product" not in result.metadata

    def test_returns_none_no_match(self):
        """Returns None for unrelated advertisement."""
        parser = RazerBleParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name_no_uuid(self):
        """Returns None for ad with no local_name and no matching service UUID."""
        parser = RazerBleParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
