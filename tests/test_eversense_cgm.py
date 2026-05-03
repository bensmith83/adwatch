"""Tests for Senseonics Eversense CGM plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.eversense_cgm import EversenseCgmParser, EVERSENSE_SERVICE_UUID


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
        name="eversense_cgm",
        service_uuid=EVERSENSE_SERVICE_UUID,
        description="Eversense",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(EversenseCgmParser):
        pass
    return _P


class TestEversense:
    def test_match_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[EVERSENSE_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_parse_basics(self):
        result = EversenseCgmParser().parse(_make_ad(service_uuids=[EVERSENSE_SERVICE_UUID]))
        assert result.metadata["product"] == "Eversense E3 CGM"
        assert result.parser_name == "eversense_cgm"
        assert result.device_class == "medical"

    def test_returns_none_unrelated(self):
        assert EversenseCgmParser().parse(_make_ad(local_name="other")) is None
