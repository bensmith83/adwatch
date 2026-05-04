"""Tests for Chamberlain myQ / Tend / Lockitron plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.chamberlain_myq import (
    ChamberlainMyqParser,
    CHUB_UUID,
    TEND_UUID,
    LOCKITRON_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="chamberlain_myq",
                     service_uuid=[CHUB_UUID, TEND_UUID, LOCKITRON_UUID],
                     local_name_pattern=r"^Lynx",
                     description="Chamberlain", version="1.0.0", core=False,
                     registry=registry)
    class _P(ChamberlainMyqParser):
        pass
    return _P


class TestChamberlainMatching:
    def test_match_chub_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[CHUB_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_tend_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TEND_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_lockitron_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[LOCKITRON_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_lynx_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Lynx-12345")
        assert len(registry.match(ad)) == 1


class TestChamberlainParsing:
    def test_chub_classification(self):
        ad = _make_ad(service_uuids=[CHUB_UUID])
        result = ChamberlainMyqParser().parse(ad)
        assert result is not None
        assert result.metadata["product_class"] == "garage_hub"
        assert result.device_class == "garage_door"

    def test_tend_classification(self):
        ad = _make_ad(service_uuids=[TEND_UUID])
        result = ChamberlainMyqParser().parse(ad)
        assert result.metadata["product_class"] == "tend_camera"
        assert result.device_class == "camera"

    def test_lockitron_classification(self):
        ad = _make_ad(service_uuids=[LOCKITRON_UUID])
        result = ChamberlainMyqParser().parse(ad)
        assert result.metadata["product_class"] == "lockitron"
        assert result.device_class == "lock"

    def test_lynx_name_without_uuid(self):
        ad = _make_ad(local_name="Lynx-Camera-001")
        result = ChamberlainMyqParser().parse(ad)
        assert result is not None
        assert result.metadata["product_class"] == "tend_camera"
        assert result.metadata["device_name"] == "Lynx-Camera-001"

    def test_legacy_lockitron_flag(self):
        ad = _make_ad(service_uuids=[LOCKITRON_UUID])
        result = ChamberlainMyqParser().parse(ad)
        assert result.metadata["legacy_product"] is True

    def test_basics(self):
        ad = _make_ad(service_uuids=[CHUB_UUID])
        result = ChamberlainMyqParser().parse(ad)
        assert result.parser_name == "chamberlain_myq"
        assert result.beacon_type == "chamberlain_myq"

    def test_returns_none_unrelated(self):
        assert ChamberlainMyqParser().parse(_make_ad(local_name="Other")) is None
