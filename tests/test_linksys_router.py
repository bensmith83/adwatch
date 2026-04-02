"""Tests for Linksys WiFi router BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.linksys_router import LinksysRouterParser, LINKSYS_UUID


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
        name="linksys",
        service_uuid=LINKSYS_UUID,
        local_name_pattern=r"^Linksys$",
        description="Linksys WiFi router advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(LinksysRouterParser):
        pass

    return registry


class TestLinksysRouterRegistry:
    def test_matches_local_name(self):
        """Matches on local_name 'Linksys' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="Linksys")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_service_uuid(self):
        """Matches when service_uuids contains the Linksys UUID."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["00002080-8eab-46c2-b788-0e9440016fd1"])
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestLinksysRouterParser:
    def test_parser_name(self):
        """parser_name is 'linksys'."""
        parser = LinksysRouterParser()
        ad = _make_ad(local_name="Linksys")
        result = parser.parse(ad)
        assert result.parser_name == "linksys"

    def test_beacon_type(self):
        """beacon_type is 'linksys'."""
        parser = LinksysRouterParser()
        ad = _make_ad(local_name="Linksys")
        result = parser.parse(ad)
        assert result.beacon_type == "linksys"

    def test_device_class(self):
        """device_class is 'router'."""
        parser = LinksysRouterParser()
        ad = _make_ad(local_name="Linksys")
        result = parser.parse(ad)
        assert result.device_class == "router"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'Linksys'."""
        parser = LinksysRouterParser()
        ad = _make_ad(local_name="Linksys")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Linksys"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:linksys)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = LinksysRouterParser()
        ad = _make_ad(local_name="Linksys", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:linksys".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_uuid_match_without_name(self):
        """Parses with service_uuid match even when local_name is None."""
        parser = LinksysRouterParser()
        ad = _make_ad(service_uuids=["00002080-8eab-46c2-b788-0e9440016fd1"])
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "linksys"

    def test_returns_none_no_match(self):
        """Returns None for unrelated advertisement."""
        parser = LinksysRouterParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name_no_uuid(self):
        """Returns None for ad with no local_name and no matching service UUID."""
        parser = LinksysRouterParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
