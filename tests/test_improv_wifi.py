"""Tests for Improv Wi-Fi (ESPHome) plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.improv_wifi import (
    ImprovWifiParser,
    IMPROV_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="improv_wifi", service_uuid=IMPROV_SERVICE_UUID,
                     description="Improv", version="1.0.0", core=False,
                     registry=registry)
    class _P(ImprovWifiParser):
        pass
    return _P


class TestImprovMatching:
    def test_match_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[IMPROV_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000fe07-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 0


class TestImprovParsing:
    def test_basics(self):
        ad = _make_ad(service_uuids=[IMPROV_SERVICE_UUID])
        result = ImprovWifiParser().parse(ad)
        assert result is not None
        assert result.parser_name == "improv_wifi"
        assert result.beacon_type == "improv_wifi"
        assert result.device_class == "provisioning"

    def test_provisioning_flag(self):
        ad = _make_ad(service_uuids=[IMPROV_SERVICE_UUID])
        result = ImprovWifiParser().parse(ad)
        assert result.metadata["provisioning_mode"] is True

    def test_local_name_surfaced(self):
        ad = _make_ad(service_uuids=[IMPROV_SERVICE_UUID], local_name="esphome-kettle")
        result = ImprovWifiParser().parse(ad)
        assert result.metadata["device_name"] == "esphome-kettle"

    def test_returns_none_no_uuid(self):
        ad = _make_ad(local_name="something")
        assert ImprovWifiParser().parse(ad) is None
