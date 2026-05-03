"""Tests for FitBark pet collar plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.fitbark import (
    FitbarkParser,
    FITBARK_V1_UUID,
    FITBARK_V2_UUID,
    FITBARK_LEGACY_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="fitbark",
                     service_uuid=[FITBARK_V1_UUID, FITBARK_V2_UUID, FITBARK_LEGACY_UUID],
                     description="FitBark", version="1.0.0", core=False, registry=registry)
    class _P(FitbarkParser):
        pass
    return _P


class TestFitbarkMatching:
    def test_match_v1_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[FITBARK_V1_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_v2_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[FITBARK_V2_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_legacy_ffa0(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["ffa0"])
        assert len(registry.match(ad)) == 1


class TestFitbarkParsing:
    def test_v1_classification(self):
        ad = _make_ad(service_uuids=[FITBARK_V1_UUID])
        result = FitbarkParser().parse(ad)
        assert result is not None
        assert result.metadata["generation"] == "v1"

    def test_v2_classification(self):
        ad = _make_ad(service_uuids=[FITBARK_V2_UUID])
        result = FitbarkParser().parse(ad)
        assert result.metadata["generation"] == "v2_plus"

    def test_legacy_uuid_classified_as_v1(self):
        ad = _make_ad(service_uuids=["ffa0"])
        result = FitbarkParser().parse(ad)
        assert result.metadata["generation"] == "v1"

    def test_basics(self):
        ad = _make_ad(service_uuids=[FITBARK_V2_UUID])
        result = FitbarkParser().parse(ad)
        assert result.parser_name == "fitbark"
        assert result.beacon_type == "fitbark"
        assert result.device_class == "pet_tracker"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert FitbarkParser().parse(ad) is None
