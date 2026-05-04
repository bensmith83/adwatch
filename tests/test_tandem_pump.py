"""Tests for Tandem t:slim X2 + Libre 3 plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tandem_pump import TandemPumpParser, TANDEM_PUMP_UUID, LIBRE3_UUID


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="tandem_pump",
        service_uuid=(TANDEM_PUMP_UUID, LIBRE3_UUID),
        local_name_pattern=r"^ABBOTT",
        description="Tandem",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(TandemPumpParser):
        pass
    return _P


class TestTandemMatching:
    def test_match_pump_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TANDEM_PUMP_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_libre3_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[LIBRE3_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_abbott_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="ABBOTT3F123ABC")
        assert len(registry.match(ad)) == 1


class TestTandemParsing:
    def test_pump_kind(self):
        result = TandemPumpParser().parse(_make_ad(service_uuids=[TANDEM_PUMP_UUID]))
        assert result.metadata["device_kind"] == "tslim_x2_pump"
        assert result.metadata["safety_critical"] is True

    def test_libre3_kind_with_serial(self):
        result = TandemPumpParser().parse(_make_ad(local_name="ABBOTT3F123ABC"))
        assert result.metadata["device_kind"] == "libre3_cgm"
        assert result.metadata["sensor_serial"] == "3F123ABC"

    def test_hybrid_closed_loop(self):
        result = TandemPumpParser().parse(_make_ad(
            service_uuids=[TANDEM_PUMP_UUID, LIBRE3_UUID],
            local_name="ABBOTTABC123",
        ))
        assert result.metadata["therapy_mode"] == "hybrid_closed_loop"

    def test_identity_uses_libre_serial(self):
        ad = _make_ad(local_name="ABBOTTSERIAL01", mac_address="11:22:33:44:55:66")
        result = TandemPumpParser().parse(ad)
        expected = hashlib.sha256(b"libre3:SERIAL01").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert TandemPumpParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = TandemPumpParser().parse(_make_ad(service_uuids=[TANDEM_PUMP_UUID]))
        assert result.parser_name == "tandem_pump"
        assert result.device_class == "medical"
