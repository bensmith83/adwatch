"""Tests for Philips DreamStation 2 plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.philips_dreamstation import (
    PhilipsDreamstationParser,
    DREAMSTATION2_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="philips_dreamstation",
                     service_uuid=DREAMSTATION2_UUID,
                     description="Philips DS2", version="1.0.0", core=False,
                     registry=registry)
    class _P(PhilipsDreamstationParser):
        pass
    return _P


class TestPhilipsDreamstationMatching:
    def test_match_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[DREAMSTATION2_UUID])
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["fe07"])
        assert len(registry.match(ad)) == 0


class TestPhilipsDreamstationParsing:
    def test_basics(self):
        ad = _make_ad(service_uuids=[DREAMSTATION2_UUID])
        result = PhilipsDreamstationParser().parse(ad)
        assert result is not None
        assert result.parser_name == "philips_dreamstation"
        assert result.beacon_type == "philips_dreamstation"
        assert result.device_class == "cpap"

    def test_metadata(self):
        ad = _make_ad(service_uuids=[DREAMSTATION2_UUID])
        result = PhilipsDreamstationParser().parse(ad)
        assert result.metadata["product_family"] == "DreamStation 2"
        assert result.metadata["safety_critical"] is True

    def test_local_name_surfaced(self):
        ad = _make_ad(service_uuids=[DREAMSTATION2_UUID], local_name="DreamStation 2")
        result = PhilipsDreamstationParser().parse(ad)
        assert result.metadata["device_name"] == "DreamStation 2"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert PhilipsDreamstationParser().parse(ad) is None
