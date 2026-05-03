"""Tests for Lezyne GPS cycling computer plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.lezyne import LezyneParser, LEZYNE_SERVICE_UUID


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="lezyne", service_uuid=LEZYNE_SERVICE_UUID,
                     description="Lezyne", version="1.0.0", core=False, registry=registry)
    class _P(LezyneParser):
        pass
    return _P


class TestLezyneMatching:
    def test_match_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[LEZYNE_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_uuid_via_service_data(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_data={LEZYNE_SERVICE_UUID: b"\x01"})
        assert len(registry.match(ad)) == 1


class TestLezyneParsing:
    def test_basics(self):
        ad = _make_ad(service_uuids=[LEZYNE_SERVICE_UUID])
        result = LezyneParser().parse(ad)
        assert result is not None
        assert result.parser_name == "lezyne"
        assert result.beacon_type == "lezyne"
        assert result.device_class == "cycling_computer"

    def test_local_name_surfaced(self):
        ad = _make_ad(service_uuids=[LEZYNE_SERVICE_UUID], local_name="Mega XL")
        result = LezyneParser().parse(ad)
        assert result.metadata["device_name"] == "Mega XL"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert LezyneParser().parse(ad) is None
