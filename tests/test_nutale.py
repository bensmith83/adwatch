"""Tests for Nutale tracker BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nutale import NutaleParser, NUTALE_NAME_RE


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
        name="nutale",
        local_name_pattern=r"^Nutale",
        description="Nutale tracker advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(NutaleParser):
        pass

    return registry


class TestNutaleParser:
    def test_matches_local_name_pattern(self):
        """Matches on local_name starting with 'Nutale'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Nutale Tracker")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_nutale_exact(self):
        """Matches on local_name that is exactly 'Nutale'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Nutale")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_without_nutale_prefix(self):
        """Does not match names that don't start with 'Nutale'."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0

    def test_parser_name(self):
        """parser_name is 'nutale'."""
        parser = NutaleParser()
        ad = _make_ad(local_name="Nutale Tracker")
        result = parser.parse(ad)
        assert result.parser_name == "nutale"

    def test_beacon_type(self):
        """beacon_type is 'nutale'."""
        parser = NutaleParser()
        ad = _make_ad(local_name="Nutale Tracker")
        result = parser.parse(ad)
        assert result.beacon_type == "nutale"

    def test_device_class(self):
        """device_class is 'tracker'."""
        parser = NutaleParser()
        ad = _make_ad(local_name="Nutale Tracker")
        result = parser.parse(ad)
        assert result.device_class == "tracker"

    def test_metadata_device_name(self):
        """metadata contains device_name from local_name."""
        parser = NutaleParser()
        ad = _make_ad(local_name="Nutale Key Finder")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Nutale Key Finder"

    def test_identity_hash_format(self):
        """Identity hash is SHA256('nutale:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = NutaleParser()
        ad = _make_ad(local_name="Nutale Tracker", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"nutale:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_varies_by_mac(self):
        """Different MAC addresses produce different identity hashes."""
        parser = NutaleParser()
        ad1 = _make_ad(local_name="Nutale Tracker", mac_address="AA:BB:CC:DD:EE:FF")
        ad2 = _make_ad(local_name="Nutale Tracker", mac_address="11:22:33:44:55:66")
        r1 = parser.parse(ad1)
        r2 = parser.parse(ad2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_raw_payload_hex_empty(self):
        """raw_payload_hex is empty string."""
        parser = NutaleParser()
        ad = _make_ad(local_name="Nutale Tracker")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_returns_none_for_none_local_name(self):
        """Returns None when local_name is None."""
        parser = NutaleParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_non_matching_name(self):
        """Returns None when local_name doesn't match pattern."""
        parser = NutaleParser()
        ad = _make_ad(local_name="Tile Tracker")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_partial_match(self):
        """Returns None when 'Nutale' appears mid-string but not at start."""
        parser = NutaleParser()
        ad = _make_ad(local_name="MyNutale Device")
        result = parser.parse(ad)
        assert result is None

    def test_nutale_name_regex(self):
        """NUTALE_NAME_RE matches names starting with 'Nutale'."""
        assert NUTALE_NAME_RE.search("Nutale") is not None
        assert NUTALE_NAME_RE.search("Nutale Tracker") is not None
        assert NUTALE_NAME_RE.search("NotNutale") is None
        assert NUTALE_NAME_RE.search("") is None

    def test_parse_via_registry(self):
        """Full round-trip: registry match + parse returns valid result."""
        registry = _make_registry()
        ad = _make_ad(local_name="Nutale Mini")
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "nutale"
        assert result.metadata["device_name"] == "Nutale Mini"
