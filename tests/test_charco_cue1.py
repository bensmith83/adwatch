"""Tests for the Charco Neurotech CUE1 plugin (presence only).

Per apk-ble-hunting/reports/charco-cue1_passive.md: the app is React Native +
Hermes bytecode with no Java scan code, so the only recoverable discriminators
are the device-name tokens `CUE1`, `CUE1+`, `CUE1-`. The Nordic UART Service
UUID is expected but is generic to every NUS peripheral, so it is never a match
criterion. No manufacturer-data layout exists, so none is claimed.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.charco_cue1 import (
    CharcoCue1Parser,
    NORDIC_UART_SERVICE_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "CUE1",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="charco_cue1",
        local_name_pattern=r"(?i)^cue1",
        description="CUE1",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(CharcoCue1Parser):
        pass

    return _P


class TestCue1Constants:
    def test_nus_uuid(self):
        assert NORDIC_UART_SERVICE_UUID == "6e400001-b5a3-f393-e0a9-e50e24dcc0e0"


class TestCue1Matching:
    def test_match_plain_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="CUE1"))) == 1

    def test_match_plus_and_minus_variants(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="CUE1+"))) == 1
        assert len(registry.match(_make_ad(local_name="CUE1-0042"))) == 1

    def test_nus_uuid_alone_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Nordic_Blinky",
                      service_uuids=[NORDIC_UART_SERVICE_UUID])
        assert registry.match(ad) == []


class TestCue1Parse:
    def test_plain_name(self):
        result = CharcoCue1Parser().parse(_make_ad(local_name="CUE1"))
        assert result is not None
        assert result.parser_name == "charco_cue1"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Charco Neurotech"
        assert result.metadata["model"] == "CUE1"
        assert result.metadata["device_name"] == "CUE1"

    def test_plus_variant(self):
        result = CharcoCue1Parser().parse(_make_ad(local_name="CUE1+"))
        assert result.metadata["model"] == "CUE1+"

    def test_name_suffix_captured(self):
        result = CharcoCue1Parser().parse(_make_ad(local_name="CUE1-0042"))
        assert result.metadata["model"] == "CUE1"
        assert result.metadata["name_suffix"] == "0042"

    def test_nus_uuid_recorded_as_corroboration(self):
        result = CharcoCue1Parser().parse(
            _make_ad(service_uuids=[NORDIC_UART_SERVICE_UUID.upper()])
        )
        assert result.metadata["nordic_uart_service"] is True

    def test_nus_absent_not_claimed(self):
        result = CharcoCue1Parser().parse(_make_ad())
        assert "nordic_uart_service" not in result.metadata

    def test_no_telemetry_claimed(self):
        result = CharcoCue1Parser().parse(
            _make_ad(manufacturer_data=b"\x59\x00\xde\xad\xbe\xef")
        )
        assert "battery_percent" not in result.metadata
        assert "stimulation_strength" not in result.metadata
        assert result.metadata["payload_hex"] == "deadbeef"

    def test_identity_hash_mac_based(self):
        result = CharcoCue1Parser().parse(_make_ad())
        expected = hashlib.sha256(b"charco_cue1:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_unrelated_returns_none(self):
        assert CharcoCue1Parser().parse(_make_ad(local_name="CUE Fitness")) is None

    def test_no_name_returns_none(self):
        assert CharcoCue1Parser().parse(_make_ad(local_name=None)) is None
