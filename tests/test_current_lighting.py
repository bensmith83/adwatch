"""Tests for HLI Solutions / GE Current Lighting sensor BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.current_lighting import (
    CurrentLightingParser,
    HLI_COMPANY_ID,
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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="current_lighting",
        company_id=HLI_COMPANY_ID,
        description="HLI Solutions / GE Current lighting sensors",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(CurrentLightingParser):
        pass

    return registry


def _hli_mfr_data(zone_id=0x29, local_name=None):
    """Build HLI manufacturer data with given zone ID."""
    return bytes([
        0xDF, 0x06,  # company ID LE
        0x00, 0x7E,  # protocol version / device type
        0x00, 0x00, 0x00, 0x01,  # header
        0x01,  # unknown
        0xFE, 0xFF,  # channel/config
        0x7F,  # unknown
        0x00,  # unknown
        zone_id,  # zone/sensor ID
        0x01, 0x05, 0x92,  # trailer
    ])


class TestCurrentLightingParser:
    def test_matches_company_id(self):
        """Registry matches on HLI company ID 0x06DF."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_parser_name(self):
        """parser_name is 'current_lighting'."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "current_lighting"

    def test_beacon_type(self):
        """beacon_type is 'current_lighting'."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "current_lighting"

    def test_device_class(self):
        """device_class is 'sensor'."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        result = parser.parse(ad)
        assert result.device_class == "sensor"

    def test_identity_hash(self):
        """Identity hash is SHA256(current_lighting:mac)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"current_lighting:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_zone_id_extracted(self):
        """Zone ID byte is extracted into metadata."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data(zone_id=0x29))
        result = parser.parse(ad)
        assert result.metadata["zone_id"] == 0x29

    def test_zone_id_varies(self):
        """Different zone IDs produce different metadata values."""
        parser = CurrentLightingParser()
        for zone in [0x20, 0x29, 0x33]:
            ad = _make_ad(manufacturer_data=_hli_mfr_data(zone_id=zone))
            result = parser.parse(ad)
            assert result.metadata["zone_id"] == zone

    def test_device_type_extracted(self):
        """Device type byte is extracted into metadata."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["device_type"] == 0x7E

    def test_room_name_from_local_name(self):
        """Room name is extracted from local_name when present."""
        parser = CurrentLightingParser()
        ad = _make_ad(
            manufacturer_data=_hli_mfr_data(),
            local_name="235 Open Office",
        )
        result = parser.parse(ad)
        assert result.metadata["room_name"] == "235 Open Office"

    def test_no_room_name_when_no_local_name(self):
        """room_name not in metadata when local_name is absent."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        result = parser.parse(ad)
        assert "room_name" not in result.metadata

    def test_raw_payload_hex(self):
        """raw_payload_hex contains payload after company ID."""
        parser = CurrentLightingParser()
        mfr = _hli_mfr_data(zone_id=0x29)
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr[2:].hex()

    def test_returns_none_wrong_company_id(self):
        """Returns None for non-HLI company ID."""
        parser = CurrentLightingParser()
        data = (0x004C).to_bytes(2, "little") + b"\x00" * 15
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = CurrentLightingParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_data(self):
        """Returns None when manufacturer_data is too short."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=b"\xDF\x06\x00")
        result = parser.parse(ad)
        assert result is None

    def test_payload_length_in_metadata(self):
        """payload_length reflects byte count after company ID."""
        parser = CurrentLightingParser()
        ad = _make_ad(manufacturer_data=_hli_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["payload_length"] == 15
