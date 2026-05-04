"""Tests for Lemur BlueDriver / VHC plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.lemur_bluedriver import (
    LemurBluedriverParser,
    BLUEDRIVER_SERVICE_UUID,
)


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
        name="lemur_bluedriver",
        service_uuid=BLUEDRIVER_SERVICE_UUID,
        local_name_pattern=r"(?i)^(BlueDriver|VHC)",
        description="BlueDriver",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(LemurBluedriverParser):
        pass

    return _P


class TestBlueDriverMatching:
    def test_match_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BLUEDRIVER_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_bluedriver_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="BlueDriver-1234")
        assert len(registry.match(ad)) == 1

    def test_match_vhc_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="VHC ABCD")
        assert len(registry.match(ad)) == 1


class TestBlueDriverParsing:
    def test_bluedriver_family(self):
        result = LemurBluedriverParser().parse(_make_ad(local_name="BlueDriver"))
        assert result.metadata["product_family"] == "bluedriver"

    def test_vhc_family(self):
        result = LemurBluedriverParser().parse(_make_ad(local_name="VHC ABCD"))
        assert result.metadata["product_family"] == "vhc"

    def test_uuid_only_match_unknown_family(self):
        result = LemurBluedriverParser().parse(_make_ad(service_uuids=[BLUEDRIVER_SERVICE_UUID]))
        assert result.metadata["product_family"] == "unknown"

    def test_returns_none_unrelated(self):
        assert LemurBluedriverParser().parse(_make_ad(local_name="Some OBD")) is None

    def test_parse_basics(self):
        result = LemurBluedriverParser().parse(_make_ad(local_name="BlueDriver"))
        assert result.parser_name == "lemur_bluedriver"
        assert result.device_class == "obd2"
