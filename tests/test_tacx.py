"""Tests for Tacx smart trainer plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tacx import (
    TacxParser,
    TACX_NEO_FLUX_UUID,
    TACX_SMART_BIKE_UUIDS,
    TACX_LEGACY_UUIDS,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="tacx",
                     service_uuid=[TACX_NEO_FLUX_UUID] + TACX_SMART_BIKE_UUIDS + TACX_LEGACY_UUIDS,
                     local_name_pattern=r"^TACX ",
                     description="Tacx", version="1.0.0", core=False, registry=registry)
    class _P(TacxParser):
        pass
    return _P


class TestTacxMatching:
    def test_match_neo_flux(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TACX_NEO_FLUX_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_smart_bike(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TACX_SMART_BIKE_UUIDS[0]])
        assert len(registry.match(ad)) == 1

    def test_match_legacy(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TACX_LEGACY_UUIDS[0]])
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="TACX NEO 12345")
        assert len(registry.match(ad)) == 1


class TestTacxParsing:
    def test_neo_flux_family_tag(self):
        ad = _make_ad(service_uuids=[TACX_NEO_FLUX_UUID])
        result = TacxParser().parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "neo_flux"

    def test_smart_bike_family_tag(self):
        ad = _make_ad(service_uuids=[TACX_SMART_BIKE_UUIDS[0]])
        result = TacxParser().parse(ad)
        assert result.metadata["product_family"] == "smart_bike"

    def test_legacy_family_tag(self):
        ad = _make_ad(service_uuids=[TACX_LEGACY_UUIDS[2]])
        result = TacxParser().parse(ad)
        assert result.metadata["product_family"] == "legacy"

    def test_name_only_matches(self):
        ad = _make_ad(local_name="TACX FLUX 67890")
        result = TacxParser().parse(ad)
        assert result is not None
        assert result.metadata["device_name"] == "TACX FLUX 67890"

    def test_basics(self):
        ad = _make_ad(service_uuids=[TACX_NEO_FLUX_UUID])
        result = TacxParser().parse(ad)
        assert result.parser_name == "tacx"
        assert result.beacon_type == "tacx"
        assert result.device_class == "smart_trainer"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert TacxParser().parse(ad) is None
