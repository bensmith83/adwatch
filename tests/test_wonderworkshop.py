"""Tests for Wonder Workshop Dash/Cue/Dot plugin."""

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.wonderworkshop import (
    WonderWorkshopParser,
    DASH_UUID,
    CUE_DOT_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="wonderworkshop", service_uuid=[DASH_UUID, CUE_DOT_UUID],
                     description="WW", version="1.0.0", core=False, registry=registry)
    class _P(WonderWorkshopParser):
        pass
    return _P


class TestWonderWorkshopMatching:
    def test_match_dash(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[DASH_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_cue_dot(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[CUE_DOT_UUID])
        assert len(registry.match(ad)) == 1


class TestWonderWorkshopParsing:
    def test_dash_robot(self):
        ad = _make_ad(service_uuids=[DASH_UUID])
        result = WonderWorkshopParser().parse(ad)
        assert result is not None
        assert result.metadata["robot"] == "Dash"

    def test_cue_dot_robot(self):
        ad = _make_ad(service_uuids=[CUE_DOT_UUID])
        result = WonderWorkshopParser().parse(ad)
        assert result.metadata["robot"] == "Cue/Dot"

    def test_local_name_surfaced(self):
        ad = _make_ad(service_uuids=[DASH_UUID], local_name="Dash 0123")
        result = WonderWorkshopParser().parse(ad)
        assert result.metadata["device_name"] == "Dash 0123"

    def test_basics(self):
        ad = _make_ad(service_uuids=[DASH_UUID])
        result = WonderWorkshopParser().parse(ad)
        assert result.parser_name == "wonderworkshop"
        assert result.beacon_type == "wonderworkshop"
        assert result.device_class == "robot_toy"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert WonderWorkshopParser().parse(ad) is None
