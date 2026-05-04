"""Tests for Honeywell/Resideo Lyric plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.honeywell_lyric import (
    HoneywellLyricParser,
    LYRIC_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="honeywell_lyric",
                     service_uuid=LYRIC_SERVICE_UUID,
                     local_name_pattern=r"^HON_NP",
                     description="Honeywell Lyric", version="1.0.0", core=False,
                     registry=registry)
    class _P(HoneywellLyricParser):
        pass
    return _P


class TestHoneywellLyricMatching:
    def test_match_name_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="HON_NP_123456")
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[LYRIC_SERVICE_UUID])
        assert len(registry.match(ad)) == 1


class TestHoneywellLyricParsing:
    def test_extract_serial_suffix(self):
        ad = _make_ad(local_name="HON_NP_ABCD1234")
        result = HoneywellLyricParser().parse(ad)
        assert result is not None
        assert result.metadata["serial_suffix"] == "ABCD1234"

    def test_no_suffix_bare_prefix(self):
        ad = _make_ad(local_name="HON_NP")
        result = HoneywellLyricParser().parse(ad)
        assert result is not None
        assert "serial_suffix" not in result.metadata

    def test_unprovisioned_flag(self):
        ad = _make_ad(local_name="HON_NP_X")
        result = HoneywellLyricParser().parse(ad)
        assert result.metadata["unprovisioned"] is True

    def test_identity_uses_serial_suffix(self):
        ad = _make_ad(local_name="HON_NP_DEADBEEF",
                      mac_address="11:22:33:44:55:66")
        result = HoneywellLyricParser().parse(ad)
        expected = hashlib.sha256(b"honeywell_lyric:DEADBEEF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        ad = _make_ad(local_name="HON_NP_X")
        result = HoneywellLyricParser().parse(ad)
        assert result.parser_name == "honeywell_lyric"
        assert result.beacon_type == "honeywell_lyric"
        assert result.device_class == "thermostat"

    def test_returns_none_unrelated(self):
        assert HoneywellLyricParser().parse(_make_ad(local_name="Other")) is None
