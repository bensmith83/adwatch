"""Tests for Huami Mi Band / Amazfit plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.huami_amazfit import (
    HuamiAmazfitParser,
    MIBAND_LEGACY_UUID,
    HUAMI_NEW_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="huami_amazfit",
                     service_uuid=[MIBAND_LEGACY_UUID, HUAMI_NEW_UUID],
                     local_name_pattern=r"^(MI Band|Mi Smart Band|Amazfit|Zepp)",
                     description="Huami", version="1.0.0", core=False,
                     registry=registry)
    class _P(HuamiAmazfitParser):
        pass
    return _P


class TestHuamiMatching:
    def test_match_legacy_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MIBAND_LEGACY_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_new_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_amazfit_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Amazfit Bip")
        assert len(registry.match(ad)) == 1

    def test_match_mi_smart_band(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Mi Smart Band 6")
        assert len(registry.match(ad)) == 1


class TestHuamiParsing:
    def test_legacy_uuid_classified_as_miband_legacy(self):
        ad = _make_ad(service_uuids=[MIBAND_LEGACY_UUID])
        result = HuamiAmazfitParser().parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "mi_band_legacy"

    def test_new_uuid_classified_as_huami_new(self):
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["product_family"] == "huami_new"

    def test_amazfit_name_extracted(self):
        ad = _make_ad(local_name="Amazfit Bip")
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["device_name"] == "Amazfit Bip"
        assert result.metadata["model_hint"] == "Bip"

    def test_amazfit_gtr_42mm(self):
        ad = _make_ad(local_name="Amazfit GTR 42mm")
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["model_hint"] == "GTR 42mm"

    def test_mi_band_4(self):
        ad = _make_ad(local_name="Mi Smart Band 4")
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["model_hint"] == "Smart Band 4"

    def test_basics(self):
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        result = HuamiAmazfitParser().parse(ad)
        assert result.parser_name == "huami_amazfit"
        assert result.beacon_type == "huami_amazfit"
        assert result.device_class == "wearable"

    def test_returns_none_unrelated(self):
        assert HuamiAmazfitParser().parse(_make_ad(local_name="Other")) is None
