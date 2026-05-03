"""Tests for Suunto wearable plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.suunto import (
    SuuntoParser,
    SUUNTO_NG_UUID,
    SUUNTO_NSP_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="suunto",
                     service_uuid=[SUUNTO_NG_UUID, SUUNTO_NSP_UUID],
                     local_name_pattern=r"^Suunto ",
                     description="Suunto", version="1.0.0", core=False, registry=registry)
    class _P(SuuntoParser):
        pass
    return _P


class TestSuuntoMatching:
    def test_match_ng_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[SUUNTO_NG_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_nsp_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[SUUNTO_NSP_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Suunto Race ABCDE")
        assert len(registry.match(ad)) == 1


class TestSuuntoParsing:
    def test_ng_protocol_tag(self):
        ad = _make_ad(service_uuids=[SUUNTO_NG_UUID])
        result = SuuntoParser().parse(ad)
        assert result is not None
        assert result.metadata["protocol"] == "ng"

    def test_nsp_protocol_tag(self):
        ad = _make_ad(service_uuids=[SUUNTO_NSP_UUID])
        result = SuuntoParser().parse(ad)
        assert result.metadata["protocol"] == "nsp"

    def test_name_extracts_model(self):
        ad = _make_ad(local_name="Suunto 9 Peak Pro 12345")
        result = SuuntoParser().parse(ad)
        assert result.metadata["device_name"] == "Suunto 9 Peak Pro 12345"

    def test_basics(self):
        ad = _make_ad(service_uuids=[SUUNTO_NG_UUID])
        result = SuuntoParser().parse(ad)
        assert result.parser_name == "suunto"
        assert result.beacon_type == "suunto"
        assert result.device_class == "wearable"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert SuuntoParser().parse(ad) is None
