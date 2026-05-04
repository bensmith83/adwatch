"""Tests for Sennheiser / Sonova consumer-audio plugin."""

import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.sennheiser import (
    SennheiserParser, SENNHEISER_COMPANY_ID, SONOVA_COMPANY_ID,
    SENNHEISER_SERVICE_UUID, SONOVA_SERVICE_UUID, AMBEO_POPCORN_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="sennheiser",
                     company_id=(SENNHEISER_COMPANY_ID, SONOVA_COMPANY_ID),
                     service_uuid=(SENNHEISER_SERVICE_UUID, SONOVA_SERVICE_UUID, AMBEO_POPCORN_UUID),
                     local_name_pattern=r"^(Momentum|CX|HD |IE |AMBEO|Sennheiser)",
                     description="Sennheiser", version="1.0.0", core=False, registry=registry)
    class _P(SennheiserParser):
        pass
    return _P


class TestSennheiserMatching:
    def test_match_sennheiser_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[SENNHEISER_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_sonova_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[SONOVA_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_ambeo_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[AMBEO_POPCORN_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_momentum_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Momentum 4")
        assert len(registry.match(ad)) == 1


class TestSennheiserParsing:
    def test_brand_sennheiser(self):
        result = SennheiserParser().parse(_make_ad(service_uuids=[SENNHEISER_SERVICE_UUID]))
        assert result.metadata["brand"] == "Sennheiser"

    def test_brand_sonova(self):
        result = SennheiserParser().parse(_make_ad(service_uuids=[SONOVA_SERVICE_UUID]))
        assert result.metadata["brand"] == "Sonova"

    def test_ambeo_setup_mode(self):
        result = SennheiserParser().parse(_make_ad(service_uuids=[AMBEO_POPCORN_UUID]))
        assert result.metadata["product_line"] == "AMBEO_Soundbar"
        assert result.metadata["wifi_setup_mode"] is True

    def test_le_prefix_stripped(self):
        result = SennheiserParser().parse(_make_ad(local_name="LE-Momentum 4"))
        assert result.metadata["device_name"] == "Momentum 4"

    def test_returns_none_unrelated(self):
        assert SennheiserParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = SennheiserParser().parse(_make_ad(local_name="Momentum"))
        assert result.parser_name == "sennheiser"
        assert result.device_class == "audio"
