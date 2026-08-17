"""Tests for the Compex Mini EMS plugin.

Per apk-ble-hunting/reports/yuyife-compex_passive.md — the sole discovery
signal is the 128-bit service UUID 6E401570-B5A3-F393-E0A9-E50E24DCCA9E.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.compex import CompexParser, COMPEX_SERVICE_UUID


NORDIC_UART_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "D4:36:39:AA:BB:CC",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="compex",
        service_uuid=COMPEX_SERVICE_UUID,
        description="Compex",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(CompexParser):
        pass

    return _P


class TestCompexMatching:
    def test_matches_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[COMPEX_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_uppercase_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["6E401570-B5A3-F393-E0A9-E50E24DCCA9E"])
        assert len(registry.match(ad)) == 1

    def test_does_not_match_stock_nordic_uart(self):
        """Compex reuses the NUS 128-bit suffix but with a 6E4015xx prefix."""
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(service_uuids=[NORDIC_UART_UUID])) == []


class TestCompexParsing:
    def test_parses_presence(self):
        ad = _make_ad(service_uuids=[COMPEX_SERVICE_UUID])
        result = CompexParser().parse(ad)
        assert result is not None
        assert result.parser_name == "compex"
        assert result.beacon_type == "compex"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Compex"
        assert result.metadata["product"] == "Compex Mini"

    def test_uuid_match_is_case_insensitive(self):
        ad = _make_ad(service_uuids=["6E401570-B5A3-F393-E0A9-E50E24DCCA9E"])
        assert CompexParser().parse(ad) is not None

    def test_matches_from_service_data_key(self):
        ad = _make_ad(service_data={COMPEX_SERVICE_UUID: b"\x01"})
        assert CompexParser().parse(ad) is not None

    def test_flags_sensitive_category(self):
        ad = _make_ad(service_uuids=[COMPEX_SERVICE_UUID])
        result = CompexParser().parse(ad)
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "muscle_stimulation"

    def test_no_telemetry_claimed(self):
        ad = _make_ad(service_uuids=[COMPEX_SERVICE_UUID])
        result = CompexParser().parse(ad)
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_surfaces_device_name_when_present(self):
        ad = _make_ad(service_uuids=[COMPEX_SERVICE_UUID], local_name="Mini-01")
        assert CompexParser().parse(ad).metadata["device_name"] == "Mini-01"

    def test_identity_hash_from_mac(self):
        ad = _make_ad(service_uuids=[COMPEX_SERVICE_UUID])
        result = CompexParser().parse(ad)
        expected = hashlib.sha256(b"compex:D4:36:39:AA:BB:CC").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_rejects_nordic_uart_only(self):
        assert CompexParser().parse(_make_ad(service_uuids=[NORDIC_UART_UUID])) is None

    def test_rejects_name_only(self):
        """The app applies no name filter — a name alone must not match."""
        assert CompexParser().parse(_make_ad(local_name="Compex")) is None

    def test_rejects_empty_ad(self):
        assert CompexParser().parse(_make_ad()) is None

    def test_storage_schema_is_none(self):
        assert CompexParser().storage_schema() is None
