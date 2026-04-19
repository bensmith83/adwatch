"""Tests for the Beta Bionics iLet bionic pancreas parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ilet import ILetParser, ILET_SERVICE_UUID


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="ilet",
        service_uuid=ILET_SERVICE_UUID,
        local_name_pattern=r"^iLet\d+-[0-9A-Fa-f]{4}",
        description="Beta Bionics iLet bionic pancreas",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ILetParser):
        pass

    return registry


class TestILetRegistry:
    def test_matches_on_name(self):
        registry = _make_registry()
        ad = _make_ad(local_name="iLet4-0D28")
        assert len(registry.match(ad)) >= 1

    def test_matches_on_service_uuid(self):
        registry = _make_registry()
        ad = _make_ad(service_uuids=[ILET_SERVICE_UUID])
        assert len(registry.match(ad)) >= 1

    def test_no_match_unrelated(self):
        registry = _make_registry()
        assert len(registry.match(_make_ad(local_name="OmnipodX"))) == 0


class TestILetParser:
    def test_basic_fields(self):
        parser = ILetParser()
        ad = _make_ad(
            local_name="iLet4-0D28",
            service_uuids=[ILET_SERVICE_UUID],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "ilet"
        assert result.beacon_type == "ilet"
        assert result.device_class == "medical_device"

    def test_extracts_model_and_suffix(self):
        parser = ILetParser()
        ad = _make_ad(local_name="iLet4-0D28")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "iLet4-0D28"
        assert result.metadata["hardware_rev"] == "iLet4"
        assert result.metadata["device_suffix"] == "0D28"

    def test_identity_hash_uses_suffix(self):
        """Suffix is the stable identifier. Two ads with the same suffix but
        different outer MACs should produce the same identifier_hash."""
        parser = ILetParser()
        r1 = parser.parse(_make_ad(
            mac_address="AA:BB:CC:DD:EE:01",
            local_name="iLet4-0D28",
        ))
        r2 = parser.parse(_make_ad(
            mac_address="AA:BB:CC:DD:EE:02",
            local_name="iLet4-0D28",
        ))
        assert r1.identifier_hash == r2.identifier_hash

    def test_matches_uuid_without_name(self):
        """Advertised UUID alone should still produce a parse."""
        parser = ILetParser()
        ad = _make_ad(service_uuids=[ILET_SERVICE_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert "device_suffix" not in result.metadata

    def test_returns_none_for_unrelated(self):
        parser = ILetParser()
        assert parser.parse(_make_ad(local_name="OtherPump")) is None

    def test_uuid_case_insensitive(self):
        """bleak sometimes surfaces uppercase UUIDs."""
        parser = ILetParser()
        ad = _make_ad(service_uuids=[ILET_SERVICE_UUID.upper()])
        result = parser.parse(ad)
        assert result is not None
