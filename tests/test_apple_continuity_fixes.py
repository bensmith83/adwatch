"""Tests for Apple Continuity subtype fixes (#16, #17)."""

import struct
import hashlib
import pytest
from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.parsers.apple_continuity import AppleContinuityParser


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
    @register_parser(name="apple_continuity", company_id=0x004C, description="Apple Continuity", version="2.0", core=True, registry=registry)
    class TestParser(AppleContinuityParser):
        pass
    return registry


class TestAirPlaySourceSubtype:
    def test_0x0a_returns_airplay_source_beacon_type(self):
        """Subtype 0x0A should be AirPlay Source, not Hey Siri Variant."""
        registry = _make_registry()
        # company_id LE + subtype 0x0A + length 4 + 4 bytes payload
        mfr = struct.pack("<H", 0x004C) + bytes([0x0A, 0x04]) + bytes(4)
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.beacon_type == "apple_airplay_source"
        assert result.device_class == "media"

    def test_0x0a_has_payload_hex(self):
        """AirPlay Source should include payload_hex in metadata."""
        registry = _make_registry()
        mfr = struct.pack("<H", 0x004C) + bytes([0x0A, 0x04]) + bytes([0xDE, 0xAD, 0xBE, 0xEF])
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert "payload_hex" in result.metadata
        assert result.metadata["payload_hex"] == "deadbeef"


class TestUnknownSubtypes:
    def test_0x16_returns_apple_unknown(self):
        """Subtype 0x16 should return apple_unknown, not apple_tethering_source."""
        registry = _make_registry()
        mfr = struct.pack("<H", 0x004C) + bytes([0x16, 0x04]) + bytes(4)
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.beacon_type == "apple_unknown"
        assert "subtype_hex" in result.metadata

    def test_0x16_has_subtype_hex(self):
        """Subtype 0x16 metadata should contain subtype_hex='0x16'."""
        registry = _make_registry()
        mfr = struct.pack("<H", 0x004C) + bytes([0x16, 0x04]) + bytes(4)
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["subtype_hex"] == "0x16"

    def test_0x01_returns_apple_unknown(self):
        """Subtype 0x01 should return apple_unknown."""
        registry = _make_registry()
        mfr = struct.pack("<H", 0x004C) + bytes([0x01, 0x04]) + bytes(4)
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.beacon_type == "apple_unknown"
        assert result.metadata["subtype_hex"] == "0x01"

    def test_0x01_has_device_class_phone(self):
        """Unknown subtypes should have device_class='phone'."""
        registry = _make_registry()
        mfr = struct.pack("<H", 0x004C) + bytes([0x01, 0x04]) + bytes(4)
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "phone"

    def test_unknown_has_payload_hex(self):
        """Unknown subtypes should include payload_hex in metadata."""
        registry = _make_registry()
        mfr = struct.pack("<H", 0x004C) + bytes([0x01, 0x03]) + bytes([0xAA, 0xBB, 0xCC])
        ad = _make_ad(manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["payload_hex"] == "aabbcc"
