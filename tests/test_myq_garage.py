"""Tests for Chamberlain/LiftMaster MyQ garage door BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.myq_garage import MyQGarageParser


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
        name="myq",
        local_name_pattern=r"^MyQ-",
        description="Chamberlain/LiftMaster MyQ garage door advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(MyQGarageParser):
        pass

    return registry


class TestMyQGarageRegistry:
    def test_matches_local_name_pattern(self):
        """Matches on local_name 'MyQ-75D' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="MyQ-75D")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestMyQGarageParser:
    def test_parser_name(self):
        """parser_name is 'myq'."""
        parser = MyQGarageParser()
        ad = _make_ad(local_name="MyQ-75D")
        result = parser.parse(ad)
        assert result.parser_name == "myq"

    def test_beacon_type(self):
        """beacon_type is 'myq'."""
        parser = MyQGarageParser()
        ad = _make_ad(local_name="MyQ-75D")
        result = parser.parse(ad)
        assert result.beacon_type == "myq"

    def test_device_class(self):
        """device_class is 'garage_door'."""
        parser = MyQGarageParser()
        ad = _make_ad(local_name="MyQ-75D")
        result = parser.parse(ad)
        assert result.device_class == "garage_door"

    def test_device_id_extraction(self):
        """'MyQ-75D' -> metadata['device_id'] == '75D'."""
        parser = MyQGarageParser()
        ad = _make_ad(local_name="MyQ-75D")
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "75D"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'MyQ-75D'."""
        parser = MyQGarageParser()
        ad = _make_ad(local_name="MyQ-75D")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "MyQ-75D"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:myq)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = MyQGarageParser()
        ad = _make_ad(local_name="MyQ-75D", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:myq".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_non_myq_name(self):
        """Returns None for non-MyQ name."""
        parser = MyQGarageParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name(self):
        """Returns None when local_name is None."""
        parser = MyQGarageParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
