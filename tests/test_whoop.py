"""Tests for WHOOP fitness strap plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.whoop import (
    WhoopParser,
    WHOOP_GEN4_UUID, WHOOP_MAVERICK_UUID, WHOOP_PUFFIN_UUID,
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
        name="whoop",
        service_uuid=(WHOOP_GEN4_UUID, WHOOP_MAVERICK_UUID, WHOOP_PUFFIN_UUID),
        local_name_pattern=r"^WHOOP",
        description="WHOOP",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(WhoopParser):
        pass
    return _P


class TestWhoopMatching:
    def test_match_gen4_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[WHOOP_GEN4_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_puffin_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[WHOOP_PUFFIN_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="WHOOP ABCDEF")
        assert len(registry.match(ad)) == 1


class TestWhoopParsing:
    def test_generation_from_uuid_gen4(self):
        result = WhoopParser().parse(_make_ad(service_uuids=[WHOOP_GEN4_UUID]))
        assert result.metadata["generation"] == "Gen4"

    def test_generation_from_uuid_maverick(self):
        result = WhoopParser().parse(_make_ad(service_uuids=[WHOOP_MAVERICK_UUID]))
        assert result.metadata["generation"] == "Maverick"

    def test_generation_from_uuid_puffin(self):
        result = WhoopParser().parse(_make_ad(service_uuids=[WHOOP_PUFFIN_UUID]))
        assert result.metadata["generation"] == "Puffin"

    def test_serial_extracted_from_name(self):
        result = WhoopParser().parse(_make_ad(local_name="WHOOP ABC123"))
        assert result.metadata["serial"] == "ABC123"

    def test_identity_uses_serial(self):
        ad = _make_ad(local_name="WHOOP DEADBEEF", mac_address="11:22:33:44:55:66")
        result = WhoopParser().parse(ad)
        expected = hashlib.sha256(b"whoop:DEADBEEF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert WhoopParser().parse(_make_ad(local_name="Garmin")) is None

    def test_parse_basics(self):
        result = WhoopParser().parse(_make_ad(service_uuids=[WHOOP_GEN4_UUID]))
        assert result.parser_name == "whoop"
        assert result.device_class == "wearable"
