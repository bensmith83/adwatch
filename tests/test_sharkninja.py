"""Tests for SharkNinja vacuum plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.sharkninja import (
    SharkNinjaParser,
    SHARKNINJA_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="sharkninja", service_uuid=SHARKNINJA_SERVICE_UUID,
                     description="SharkNinja", version="1.0.0", core=False,
                     registry=registry)
    class _P(SharkNinjaParser):
        pass
    return _P


class TestSharkNinjaMatching:
    def test_match_uuid_short(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["fcbb"])
        assert len(registry.match(ad)) == 1

    def test_match_uuid_full(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000fcbb-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1


class TestSharkNinjaParsing:
    def test_provisioning_flag(self):
        ad = _make_ad(service_uuids=["fcbb"])
        result = SharkNinjaParser().parse(ad)
        assert result is not None
        assert result.metadata["provisioning_mode"] is True

    def test_basics(self):
        ad = _make_ad(service_uuids=["fcbb"])
        result = SharkNinjaParser().parse(ad)
        assert result.parser_name == "sharkninja"
        assert result.beacon_type == "sharkninja"
        assert result.device_class == "vacuum"

    def test_returns_none_no_uuid(self):
        ad = _make_ad(local_name="something")
        assert SharkNinjaParser().parse(ad) is None
