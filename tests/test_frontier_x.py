"""Tests for the Fourth Frontier "Frontier X" ECG chest-strap plugin.

Per apk-ble-hunting/reports/fourthfrontier-biostrip_passive.md: discovery is
name-substring-only (`getName().contains("Frontier")`), the app parses no scan
record at all, and it stores the advertised name as the device's identity key.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.frontier_x import FrontierXParser, FRONTIER_NAME_TOKEN


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "Frontier X2 3A7F",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="frontier_x",
        local_name_pattern=r"Frontier",
        description="Frontier X",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(FrontierXParser):
        pass

    return _P


class TestFrontierConstants:
    def test_name_token(self):
        assert FRONTIER_NAME_TOKEN == "Frontier"


class TestFrontierMatching:
    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Frontier X 1234"))) == 1

    def test_match_is_case_sensitive_like_the_app(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="frontier x")) == []

    def test_no_match_without_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name=None)) == []


class TestFrontierParse:
    def test_model_x2(self):
        result = FrontierXParser().parse(_make_ad(local_name="Frontier X2 3A7F"))
        assert result is not None
        assert result.parser_name == "frontier_x"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Fourth Frontier"
        assert result.metadata["model"] == "Frontier X2"
        assert result.metadata["device_name"] == "Frontier X2 3A7F"
        assert result.metadata["name_suffix"] == "3A7F"
        assert result.metadata["vendor_attribution"] == "confirmed"

    def test_model_base_x(self):
        result = FrontierXParser().parse(_make_ad(local_name="FrontierX"))
        assert result.metadata["model"] == "Frontier X"
        assert "name_suffix" not in result.metadata

    def test_model_x3(self):
        result = FrontierXParser().parse(_make_ad(local_name="Frontier X3-0091"))
        assert result.metadata["model"] == "Frontier X3"
        assert result.metadata["name_suffix"] == "0091"

    def test_generic_frontier_name_is_uncertain(self):
        result = FrontierXParser().parse(_make_ad(local_name="Frontier Router"))
        assert result is not None
        assert result.metadata["vendor_attribution"] == "uncertain"
        assert "model" not in result.metadata

    def test_identity_hash_uses_name(self):
        result = FrontierXParser().parse(_make_ad(local_name="Frontier X2 3A7F"))
        expected = hashlib.sha256(b"frontier_x:Frontier X2 3A7F").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_mac_change(self):
        a = FrontierXParser().parse(_make_ad(local_name="Frontier X2 3A7F"))
        b = FrontierXParser().parse(
            _make_ad(local_name="Frontier X2 3A7F", mac_address="11:22:33:44:55:66")
        )
        assert a.identifier_hash == b.identifier_hash

    def test_distinct_units_get_distinct_hashes(self):
        a = FrontierXParser().parse(_make_ad(local_name="Frontier X2 3A7F"))
        b = FrontierXParser().parse(_make_ad(local_name="Frontier X2 9C11"))
        assert a.identifier_hash != b.identifier_hash

    def test_unrelated_returns_none(self):
        assert FrontierXParser().parse(_make_ad(local_name="Polar H10")) is None

    def test_no_name_returns_none(self):
        assert FrontierXParser().parse(_make_ad(local_name=None)) is None

    def test_no_advertised_payload_claimed(self):
        result = FrontierXParser().parse(_make_ad(local_name="Frontier X2 3A7F"))
        assert result.raw_payload_hex == ""
