"""Tests for iTAG BLE anti-loss tracker plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.itag import ITagParser, ITAG_UUIDS


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
        name="itag",
        service_uuid=ITAG_UUIDS,
        local_name_pattern=r"(?i)^iTAG",
        description="iTAG anti-loss tracker",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ITagParser):
        pass

    return registry


class TestITagParser:
    def test_matches_service_uuid_ffe0(self):
        """Matches service UUID ffe0."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["ffe0"])
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "itag"

    def test_matches_service_uuid_1802(self):
        """Matches service UUID 1802."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["1802"])
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None

    def test_matches_local_name_itag(self):
        """Matches local name 'iTAG'."""
        registry = _make_registry()
        ad = _make_ad(local_name="iTAG")
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None

    def test_device_class_is_tracker(self):
        """device_class is 'tracker'."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["ffe0"], local_name="iTAG")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "tracker"

    def test_returns_device_name_in_metadata(self):
        """Returns device_name in metadata."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["ffe0"], local_name="iTAG")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["device_name"] == "iTAG"

    def test_returns_none_when_no_matching_signal(self):
        """Returns None when no matching signal."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["abcd"], local_name="SomeOtherDevice")
        matches = registry.match(ad)
        if matches:
            result = matches[0].parse(ad)
            assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:itag')[:16]."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["ffe0"], mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:itag".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected
