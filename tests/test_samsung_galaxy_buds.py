"""Tests for Samsung Galaxy Buds BLE advertisement parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.samsung_galaxy_buds import (
    SamsungGalaxyBudsParser,
    BUDS_SERVICE_UUID,
    BUDS_NAME_RE,
    BUDS_MODEL_RE,
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
        name="samsung_galaxy_buds",
        service_uuid=BUDS_SERVICE_UUID,
        local_name_pattern=r"Galaxy Buds",
        description="Samsung Galaxy Buds earbuds advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(SamsungGalaxyBudsParser):
        pass

    return registry


class TestSamsungGalaxyBudsParser:
    def test_matches_service_uuid_fd69(self):
        """Matches service UUID fd69."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fd69"], service_data={"fd69": bytes([0x01, 0x02, 0x03, 0x04])})
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "samsung_galaxy_buds"

    def test_matches_local_name_galaxy_buds(self):
        """Matches local name containing 'Galaxy Buds'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds3 Pro (E757) LE")
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None

    def test_device_class_is_earbuds(self):
        """device_class is 'earbuds'."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fd69"], service_data={"fd69": bytes([0x01, 0x02, 0x03, 0x04])})
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "earbuds"

    def test_beacon_type(self):
        """beacon_type is 'samsung_galaxy_buds'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds Pro (E123) LE")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.beacon_type == "samsung_galaxy_buds"

    def test_identity_hash(self):
        """Identity hash: SHA256('samsung_galaxy_buds:{mac}')[:16]."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fd69"], mac_address="11:22:33:44:55:66",
                      service_data={"fd69": bytes([0x01, 0x02, 0x03, 0x04])})
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("samsung_galaxy_buds:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parses_service_data_fields(self):
        """Parses frame_type, device_id, and flags from fd69 service data."""
        registry = _make_registry()
        svc_data = bytes([0x42, 0x00, 0xFF, 0x03, 0xAA, 0xBB])
        ad = _make_ad(service_uuids=["fd69"], service_data={"fd69": svc_data})
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == 0x42
        assert result.metadata["device_id"] == 0x00FF
        assert result.metadata["flags"] == 0x03

    def test_extracts_model_from_local_name(self):
        """Extracts model like 'Galaxy Buds3 Pro' from local name."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds3 Pro (E757) LE")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model"] == "Galaxy Buds3 Pro"

    def test_extracts_model_galaxy_buds_live(self):
        """Extracts model 'Galaxy Buds Live' from local name."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds Live (R180) LE")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model"] == "Galaxy Buds Live"

    def test_extracts_model_galaxy_buds_plain(self):
        """Extracts model 'Galaxy Buds' from local name with simple format."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds (R170) LE")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model"] == "Galaxy Buds"

    def test_no_model_when_name_has_no_parens(self):
        """No model extracted when local name lacks parenthesized code."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds Pro")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert "model" not in result.metadata

    def test_returns_none_when_no_matching_signal(self):
        """Returns None when no matching UUID or name."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["abcd"], local_name="SomeOtherDevice")
        matches = registry.match(ad)
        if matches:
            result = matches[0].parse(ad)
            assert result is None

    def test_returns_none_bare_ad(self):
        """Returns None for a bare ad with no service data or name."""
        parser = SamsungGalaxyBudsParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_short_service_data_no_fields(self):
        """Short service data (< 4 bytes) skips field parsing."""
        registry = _make_registry()
        short_data = bytes([0x01, 0x02])
        ad = _make_ad(service_uuids=["fd69"], service_data={"fd69": short_data})
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert "frame_type" not in result.metadata
        assert "device_id" not in result.metadata
        assert "flags" not in result.metadata

    def test_raw_payload_hex_from_service_data(self):
        """raw_payload_hex is hex of fd69 service data."""
        registry = _make_registry()
        svc_data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        ad = _make_ad(service_uuids=["fd69"], service_data={"fd69": svc_data})
        result = registry.match(ad)[0].parse(ad)
        assert result.raw_payload_hex == "deadbeef"

    def test_raw_payload_hex_empty_when_no_service_data(self):
        """raw_payload_hex is empty string when no fd69 service data."""
        registry = _make_registry()
        ad = _make_ad(local_name="Galaxy Buds3 Pro (E757) LE")
        result = registry.match(ad)[0].parse(ad)
        assert result.raw_payload_hex == ""

    def test_name_match_only_sufficient(self):
        """Name match alone (without service UUID) is sufficient to parse."""
        parser = SamsungGalaxyBudsParser()
        ad = _make_ad(local_name="Galaxy Buds2 (R177) LE")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model"] == "Galaxy Buds2"

    def test_service_data_only_sufficient(self):
        """Service data match alone (without name) is sufficient to parse."""
        parser = SamsungGalaxyBudsParser()
        ad = _make_ad(service_data={"fd69": bytes([0x01, 0x02, 0x03, 0x04])})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == 0x01
