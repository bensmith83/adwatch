"""Tests for RadonEye RD200 radon detector plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.radoneye import RadonEyeParser


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


class TestRadonEyeParser:
    def test_match_by_local_name_pattern(self):
        """Should match by local_name pattern ^FR:."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:R20012345")
        assert len(registry.match(ad)) == 1

    def test_version_v1_r2(self):
        """FR:R2* → Version 1."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:R20012345")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["version"] == "V1"

    def test_version_v2_ru(self):
        """FR:RU* → Version 2."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:RU12345")
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["version"] == "V2"

    def test_version_v2_re(self):
        """FR:RE* → Version 2."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:RE12345")
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["version"] == "V2"

    def test_region_extraction(self):
        """Region should be extracted from local name prefix."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:RU12345")
        result = registry.match(ad)[0].parse(ad)
        assert "region" in result.metadata or "prefix" in result.metadata

    def test_no_match_non_fr_name(self):
        """Should not match for non-FR: names."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="SomeOtherDevice")
        assert len(registry.match(ad)) == 0

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:{local_name}')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:R20012345", mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:FR:R20012345".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self):
        """Device class should be 'sensor'."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:R20012345")
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "sensor"

    def test_beacon_type(self):
        """Beacon type should be 'radoneye'."""
        registry = ParserRegistry()

        @register_parser(
            name="radoneye", local_name_pattern=r"^FR:",
            description="RadonEye", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RadonEyeParser):
            pass

        ad = _make_ad(local_name="FR:R20012345")
        result = registry.match(ad)[0].parse(ad)
        assert result.beacon_type == "radoneye"
