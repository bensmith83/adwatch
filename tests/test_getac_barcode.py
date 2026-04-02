"""Tests for Getac rugged barcode scanner BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.getac_barcode import GetacBarcodeParser


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
        name="getac",
        local_name_pattern=r"Getac$",
        description="Getac rugged barcode scanner advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GetacBarcodeParser):
        pass

    return registry


class TestGetacBarcodeRegistry:
    def test_matches_local_name_pattern(self):
        """Matches on local_name 'BC220267720008Getac' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="BC220267720008Getac")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestGetacBarcodeParser:
    def test_parser_name(self):
        """parser_name is 'getac'."""
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="BC220267720008Getac")
        result = parser.parse(ad)
        assert result.parser_name == "getac"

    def test_beacon_type(self):
        """beacon_type is 'getac'."""
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="BC220267720008Getac")
        result = parser.parse(ad)
        assert result.beacon_type == "getac"

    def test_device_class(self):
        """device_class is 'barcode_scanner'."""
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="BC220267720008Getac")
        result = parser.parse(ad)
        assert result.device_class == "barcode_scanner"

    def test_serial_extraction(self):
        """'BC220267720008Getac' -> metadata['serial'] == 'BC220267720008'."""
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="BC220267720008Getac")
        result = parser.parse(ad)
        assert result.metadata["serial"] == "BC220267720008"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'BC220267720008Getac'."""
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="BC220267720008Getac")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "BC220267720008Getac"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:getac)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="BC220267720008Getac", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:getac".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_non_getac_name(self):
        """Returns None for non-Getac name."""
        parser = GetacBarcodeParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name(self):
        """Returns None when local_name is None."""
        parser = GetacBarcodeParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
