"""Tests for Autophix OBD2 automotive diagnostic scanner BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.autophix_obd2 import AutophixObd2Parser


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
        name="autophix",
        local_name_pattern=r"^Autophix\s",
        description="Autophix OBD2 automotive diagnostic scanner",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(AutophixObd2Parser):
        pass

    return registry


class TestAutophixObd2Registry:
    def test_matches_local_name_pattern(self):
        """Matches on local_name 'Autophix 3210' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="Autophix 3210")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestAutophixObd2Parser:
    def test_parser_name(self):
        """parser_name is 'autophix'."""
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="Autophix 3210")
        result = parser.parse(ad)
        assert result.parser_name == "autophix"

    def test_beacon_type(self):
        """beacon_type is 'autophix'."""
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="Autophix 3210")
        result = parser.parse(ad)
        assert result.beacon_type == "autophix"

    def test_device_class(self):
        """device_class is 'automotive'."""
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="Autophix 3210")
        result = parser.parse(ad)
        assert result.device_class == "automotive"

    def test_model_extraction(self):
        """'Autophix 3210' -> metadata['model'] == '3210'."""
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="Autophix 3210")
        result = parser.parse(ad)
        assert result.metadata["model"] == "3210"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'Autophix 3210'."""
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="Autophix 3210")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Autophix 3210"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:autophix)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="Autophix 3210", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:autophix".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_non_autophix_name(self):
        """Returns None for non-Autophix name."""
        parser = AutophixObd2Parser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name(self):
        """Returns None when local_name is None."""
        parser = AutophixObd2Parser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
