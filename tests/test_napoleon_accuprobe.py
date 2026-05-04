"""Tests for Napoleon ACCU-PROBE plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.napoleon_accuprobe import (
    NapoleonAccuprobeParser,
    NAPOLEON_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="napoleon_accuprobe",
                     service_uuid=NAPOLEON_SERVICE_UUID,
                     local_name_pattern=r"(NAP_KT|ACCU-PROBE)",
                     description="Napoleon", version="1.0.0", core=False,
                     registry=registry)
    class _P(NapoleonAccuprobeParser):
        pass
    return _P


class TestNapoleonMatching:
    def test_match_uuid_short(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["ff00"])
        assert len(registry.match(ad)) == 1

    def test_match_uuid_full(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000ff00-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1

    def test_match_nap_kt_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="NAP_KT_001")
        assert len(registry.match(ad)) == 1

    def test_match_accu_probe_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="ACCU-PROBE_002")
        assert len(registry.match(ad)) == 1


class TestNapoleonParsing:
    def test_v1_family_from_nap_kt(self):
        ad = _make_ad(local_name="NAP_KT_001",
                      service_uuids=["ff00"])
        result = NapoleonAccuprobeParser().parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "v1"

    def test_v2_family_from_accu_probe(self):
        ad = _make_ad(local_name="ACCU-PROBE_002",
                      service_uuids=["ff00"])
        result = NapoleonAccuprobeParser().parse(ad)
        assert result.metadata["product_family"] == "v2"

    def test_uuid_only_unknown_family(self):
        ad = _make_ad(service_uuids=["ff00"])
        result = NapoleonAccuprobeParser().parse(ad)
        assert result.metadata["product_family"] == "unknown"

    def test_basics(self):
        ad = _make_ad(local_name="NAP_KT_001", service_uuids=["ff00"])
        result = NapoleonAccuprobeParser().parse(ad)
        assert result.parser_name == "napoleon_accuprobe"
        assert result.beacon_type == "napoleon_accuprobe"
        assert result.device_class == "thermometer"

    def test_uuid_alone_without_name_still_matches(self):
        # The 0xFF00 UUID is a commodity-module SIG; we accept UUID-only
        # but require an additional signal for high confidence.
        ad = _make_ad(service_uuids=["0000ff00-0000-1000-8000-00805f9b34fb"])
        result = NapoleonAccuprobeParser().parse(ad)
        assert result is not None
        assert result.metadata["confidence"] == "low"

    def test_uuid_plus_name_high_confidence(self):
        ad = _make_ad(local_name="ACCU-PROBE_X",
                      service_uuids=["0000ff00-0000-1000-8000-00805f9b34fb"])
        result = NapoleonAccuprobeParser().parse(ad)
        assert result.metadata["confidence"] == "high"

    def test_returns_none_unrelated(self):
        assert NapoleonAccuprobeParser().parse(_make_ad(local_name="Other")) is None
