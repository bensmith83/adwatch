"""Tests for ELK-BLEDOM LED light strip BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.elk_bledom import ElkBledomParser, ELK_NAME_RE


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
        name="elk_bledom",
        local_name_pattern=r"^ELK-BLEDOM",
        description="ELK-BLEDOM LED light strip advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ElkBledomParser):
        pass

    return registry


class TestElkBledomParser:
    def test_matches_local_name_pattern(self):
        """Matches on local_name_pattern '^ELK-BLEDOM'."""
        registry = _make_registry()
        ad = _make_ad(local_name="ELK-BLEDOM")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_with_suffix(self):
        """Matches names like 'ELK-BLEDOM0000'."""
        registry = _make_registry()
        ad = _make_ad(local_name="ELK-BLEDOM0000")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_without_local_name(self):
        """Does not match when local_name is None."""
        registry = _make_registry()
        ad = _make_ad(local_name=None)
        matches = registry.match(ad)
        assert len(matches) == 0

    def test_no_match_different_name(self):
        """Does not match unrelated local names."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeLightBulb")
        matches = registry.match(ad)
        assert len(matches) == 0

    def test_parse_returns_result(self):
        """Parse returns a ParseResult for matching ads."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM")
        result = parser.parse(ad)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self):
        """parser_name is 'elk_bledom'."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM")
        result = parser.parse(ad)
        assert result.parser_name == "elk_bledom"

    def test_beacon_type(self):
        """beacon_type is 'elk_bledom'."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM")
        result = parser.parse(ad)
        assert result.beacon_type == "elk_bledom"

    def test_device_class_is_light(self):
        """device_class is 'light'."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM")
        result = parser.parse(ad)
        assert result.device_class == "light"

    def test_device_name_in_metadata(self):
        """metadata contains device_name matching local_name."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM0000")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "ELK-BLEDOM0000"

    def test_identity_hash_format(self):
        """Identity hash is SHA256('elk_bledom:{mac}')[:16]."""
        parser = ElkBledomParser()
        mac = "11:22:33:44:55:66"
        ad = _make_ad(local_name="ELK-BLEDOM", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"elk_bledom:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self):
        """Identity hash is 16 hex characters."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM")
        result = parser.parse(ad)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_raw_payload_hex_empty(self):
        """raw_payload_hex is empty string."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="ELK-BLEDOM")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_returns_none_for_none_local_name(self):
        """Returns None when local_name is None."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name=None)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_non_matching_name(self):
        """Returns None when local_name doesn't match pattern."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="NotAnElkDevice")
        result = parser.parse(ad)
        assert result is None

    def test_case_sensitive_no_match_lowercase(self):
        """Pattern is case-sensitive — 'elk-bledom' does not match."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="elk-bledom")
        result = parser.parse(ad)
        assert result is None

    def test_case_sensitive_no_match_mixed(self):
        """Pattern is case-sensitive — 'Elk-Bledom' does not match."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="Elk-Bledom")
        result = parser.parse(ad)
        assert result is None

    def test_name_must_start_with_pattern(self):
        """Name containing ELK-BLEDOM but not at start does not match."""
        parser = ElkBledomParser()
        ad = _make_ad(local_name="My ELK-BLEDOM Light")
        result = parser.parse(ad)
        assert result is None

    def test_different_macs_produce_different_hashes(self):
        """Different MAC addresses produce different identity hashes."""
        parser = ElkBledomParser()
        ad1 = _make_ad(local_name="ELK-BLEDOM", mac_address="AA:BB:CC:DD:EE:01")
        ad2 = _make_ad(local_name="ELK-BLEDOM", mac_address="AA:BB:CC:DD:EE:02")
        result1 = parser.parse(ad1)
        result2 = parser.parse(ad2)
        assert result1.identifier_hash != result2.identifier_hash

    def test_parse_via_registry(self):
        """End-to-end: registry match + parse returns correct result."""
        registry = _make_registry()
        ad = _make_ad(local_name="ELK-BLEDOM")
        matches = registry.match(ad)
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "elk_bledom"
        assert result.device_class == "light"

    def test_elk_name_re_constant(self):
        """ELK_NAME_RE matches expected patterns."""
        assert ELK_NAME_RE.search("ELK-BLEDOM")
        assert ELK_NAME_RE.search("ELK-BLEDOM0000")
        assert not ELK_NAME_RE.search("elk-bledom")
        assert not ELK_NAME_RE.search("Something ELK-BLEDOM")
