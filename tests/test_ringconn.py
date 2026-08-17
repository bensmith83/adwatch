"""Tests for the RingConn smart-ring plugin.

Per apk-ble-hunting/reports/gdjztech-ringconn_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ringconn import RingConnParser, RINGCONN_NAME_PATTERN


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "C4:64:E3:AA:BB:CC",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="ringconn",
        local_name_pattern=RINGCONN_NAME_PATTERN,
        description="RingConn",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(RingConnParser):
        pass

    return _P


class TestRingConnMatching:
    def test_matches_exact_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="RingConn"))) == 1

    def test_matches_hyphenated_suffix(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="RingConn-1A2B"))) == 1

    def test_glued_word_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="RingConnector")) == []

    def test_mid_name_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="My RingConn")) == []

    def test_nordic_uart_uuid_not_registered(self):
        """The NUS UUID is generic and only used post-connect."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["6e400001-b5a3-f393-e0a9-e50e24dcca9e"])
        assert registry.match(ad) == []


class TestRingConnDecode:
    def test_bare_name(self):
        result = RingConnParser().parse(_make_ad(local_name="RingConn"))
        assert result is not None
        assert result.metadata["device_name"] == "RingConn"
        assert "name_suffix" not in result.metadata

    def test_name_is_not_per_device(self):
        result = RingConnParser().parse(_make_ad(local_name="RingConn"))
        assert result.metadata["name_is_unique"] is False

    def test_suffix_captured_when_present(self):
        result = RingConnParser().parse(_make_ad(local_name="RingConn-1A2B"))
        assert result.metadata["name_suffix"] == "1A2B"

    def test_space_suffix_captured(self):
        result = RingConnParser().parse(_make_ad(local_name="RingConn 7F"))
        assert result.metadata["name_suffix"] == "7F"

    def test_rejects_glued_word(self):
        assert RingConnParser().parse(_make_ad(local_name="RingConnector")) is None

    def test_rejects_missing_name(self):
        assert RingConnParser().parse(_make_ad()) is None

    def test_rejects_unrelated_name(self):
        assert RingConnParser().parse(_make_ad(local_name="Oura")) is None

    def test_no_passive_telemetry_claimed(self):
        """Health data is AES-GCM over NUS post-connect — never decoded here."""
        ad = _make_ad(local_name="RingConn", manufacturer_data=bytes([0x01, 0x02, 0x03]))
        result = RingConnParser().parse(ad)
        assert "heart_rate" not in result.metadata
        assert "battery_percent" not in result.metadata


class TestRingConnIdentityAndBasics:
    def test_identity_from_mac(self):
        ad = _make_ad(local_name="RingConn")
        result = RingConnParser().parse(ad)
        expected = hashlib.sha256(
            f"ringconn:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_differs_by_mac(self):
        a = _make_ad(local_name="RingConn", mac_address="AA:BB:CC:DD:EE:FF")
        b = _make_ad(local_name="RingConn", mac_address="11:22:33:44:55:66")
        assert RingConnParser().parse(a).identifier_hash != \
            RingConnParser().parse(b).identifier_hash

    def test_basics(self):
        result = RingConnParser().parse(_make_ad(local_name="RingConn"))
        assert result.parser_name == "ringconn"
        assert result.beacon_type == "ringconn"
        assert result.device_class == "wearable"
        assert result.metadata["vendor"] == "RingConn"
        assert result.metadata["product"] == "smart ring"
