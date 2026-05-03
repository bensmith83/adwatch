"""Tests for ThermoPro BBQ thermometer plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.thermopro_bbq import (
    ThermoProBbqParser,
    BBQ_SERVICE_UUIDS,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="thermopro_bbq",
                     service_uuid=BBQ_SERVICE_UUIDS,
                     local_name_pattern=r"^(Thermopro|TP\d{2,3}|P900|YKE-[A-Z]\d?-DFU)$",
                     description="ThermoPro BBQ", version="1.0.0", core=False,
                     registry=registry)
    class _P(ThermoProBbqParser):
        pass
    return _P


class TestThermoProBbqMatching:
    def test_match_chipset1_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BBQ_SERVICE_UUIDS[0]])
        assert len(registry.match(ad)) == 1

    def test_match_chipset2_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BBQ_SERVICE_UUIDS[1]])
        assert len(registry.match(ad)) == 1

    def test_match_chipset3_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BBQ_SERVICE_UUIDS[2]])
        assert len(registry.match(ad)) == 1

    def test_match_tp920(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="TP920")
        assert len(registry.match(ad)) == 1

    def test_match_tp25(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="TP25")
        assert len(registry.match(ad)) == 1

    def test_match_p900(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="P900")
        assert len(registry.match(ad)) == 1

    def test_match_dfu_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="YKE-D4-DFU")
        assert len(registry.match(ad)) == 1


class TestThermoProBbqParsing:
    def test_model_extracted_from_name(self):
        ad = _make_ad(local_name="TP920")
        result = ThermoProBbqParser().parse(ad)
        assert result is not None
        assert result.metadata["model"] == "TP920"

    def test_dfu_mode_flag(self):
        ad = _make_ad(local_name="YKE-D4-DFU")
        result = ThermoProBbqParser().parse(ad)
        assert result.metadata["dfu_mode"] is True
        assert result.metadata["model"] == "YKE-D4-DFU"

    def test_chipset_tag_from_uuid(self):
        ad = _make_ad(service_uuids=[BBQ_SERVICE_UUIDS[0]])
        result = ThermoProBbqParser().parse(ad)
        assert result.metadata["chipset_family"] == "fff"

    def test_chipset_tag_a3c3a55(self):
        ad = _make_ad(service_uuids=[BBQ_SERVICE_UUIDS[1]])
        result = ThermoProBbqParser().parse(ad)
        assert result.metadata["chipset_family"] == "a3c3a55"

    def test_basics(self):
        result = ThermoProBbqParser().parse(_make_ad(local_name="TP920"))
        assert result.parser_name == "thermopro_bbq"
        assert result.beacon_type == "thermopro_bbq"
        assert result.device_class == "thermometer"

    def test_returns_none_unrelated(self):
        # The classic indoor TP-series uses "TP358 (1234)" and is parsed
        # by thermopro.py — make sure we don't claim it.
        assert ThermoProBbqParser().parse(_make_ad(local_name="TP358 (1234)")) is None
