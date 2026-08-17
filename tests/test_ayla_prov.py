"""Tests for the Ayla Networks BLE Wi-Fi-setup plugin.

Source: apk-ble-hunting/reports/owletcare-sleep_passive.md — the Owlet
Dream Sock base station uses the Ayla Networks BLE setup SDK, which
advertises the SIG-assigned Ayla 16-bit UUID 0xFE28 (and optionally the
Ayla Wi-Fi-config service) while in provisioning mode.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ayla_prov import (
    AylaProvParser,
    AYLA_SERVICE_UUID,
    AYLA_WIFI_CONFIG_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="ayla_prov",
        service_uuid=[AYLA_SERVICE_UUID, AYLA_WIFI_CONFIG_UUID],
        description="Ayla Networks BLE Wi-Fi setup",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(AylaProvParser):
        pass

    return _P


class TestAylaMatching:
    def test_matches_short_fe28(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=["fe28"]))) == 1

    def test_matches_full_fe28(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000FE28-0000-1000-8000-00805F9B34FB"])
        assert len(registry.match(ad)) == 1

    def test_matches_wifi_config_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[AYLA_WIFI_CONFIG_UUID]))) == 1

    def test_no_match_unrelated_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000180f-0000-1000-8000-00805f9b34fb"])
        assert registry.match(ad) == []


class TestAylaParsing:
    def test_basics(self):
        result = AylaProvParser().parse(_make_ad(service_uuids=["fe28"]))
        assert result is not None
        assert result.parser_name == "ayla_prov"
        assert result.beacon_type == "ayla_prov"
        assert result.device_class == "provisioning"
        assert result.metadata["vendor"] == "Ayla Networks"
        assert result.metadata["setup_mode"] is True

    def test_wifi_config_service_flagged(self):
        result = AylaProvParser().parse(
            _make_ad(service_uuids=["fe28", AYLA_WIFI_CONFIG_UUID])
        )
        assert result.metadata["has_wifi_config_service"] is True
        assert result.metadata["has_identity_service"] is True

    def test_identity_only(self):
        result = AylaProvParser().parse(_make_ad(service_uuids=["fe28"]))
        assert result.metadata["has_identity_service"] is True
        assert result.metadata["has_wifi_config_service"] is False

    def test_device_name_recorded(self):
        result = AylaProvParser().parse(
            _make_ad(service_uuids=["fe28"], local_name="OwletBase-1234")
        )
        assert result.metadata["device_name"] == "OwletBase-1234"

    def test_identity_hash_is_mac_based(self):
        result = AylaProvParser().parse(_make_ad(service_uuids=["fe28"]))
        expected = hashlib.sha256(b"ayla_prov:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_without_ayla_uuid(self):
        assert AylaProvParser().parse(_make_ad(local_name="OwletBase")) is None
