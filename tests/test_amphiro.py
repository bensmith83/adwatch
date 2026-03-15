"""Tests for Amphiro smart shower head plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.amphiro import AmphiroParser


SERVICE_UUID = "7f402200-504f-4c41-5261-6d706869726f"


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


def _build_service_data(session_id, volume_raw, temp_raw, duration, energy):
    """Build 12-byte service data payload."""
    return struct.pack("<IHHHH", session_id, volume_raw, temp_raw, duration, energy)


class TestAmphiroParser:
    def _registry_and_parser(self):
        registry = ParserRegistry()

        @register_parser(
            name="amphiro",
            service_uuid=SERVICE_UUID,
            description="Amphiro smart shower head",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(AmphiroParser):
            pass

        return registry

    def test_match_by_service_uuid(self):
        """Should match advertisements with the Amphiro service UUID."""
        registry = self._registry_and_parser()
        data = _build_service_data(1, 100, 370, 120, 500)
        ad = _make_ad(service_data={SERVICE_UUID: data})
        assert len(registry.match(ad)) == 1

    def test_parse_normal_session(self):
        """Parse a normal shower session with typical values."""
        registry = self._registry_and_parser()
        # session=42, volume=355 (35.5L), temp=385 (38.5C), duration=300s, energy=1200Wh
        data = _build_service_data(42, 355, 385, 300, 1200)
        ad = _make_ad(service_data={SERVICE_UUID: data})
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "amphiro"
        assert result.beacon_type == "amphiro"
        assert result.device_class == "sensor"
        assert result.metadata["session_id"] == 42
        assert result.metadata["water_volume"] == pytest.approx(35.5)
        assert result.metadata["water_temperature"] == pytest.approx(38.5)
        assert result.metadata["duration"] == 300
        assert result.metadata["energy"] == 1200

    def test_parse_zero_values(self):
        """Parse session with all zero sensor values (start of session)."""
        registry = self._registry_and_parser()
        data = _build_service_data(1, 0, 0, 0, 0)
        ad = _make_ad(service_data={SERVICE_UUID: data})
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["session_id"] == 1
        assert result.metadata["water_volume"] == 0.0
        assert result.metadata["water_temperature"] == 0.0
        assert result.metadata["duration"] == 0
        assert result.metadata["energy"] == 0

    def test_no_service_data(self):
        """No service data returns None."""
        parser = AmphiroParser()
        ad = _make_ad(service_data=None)
        result = parser.parse(ad)
        assert result is None

    def test_wrong_service_uuid(self):
        """Service data with wrong UUID returns None."""
        parser = AmphiroParser()
        ad = _make_ad(service_data={"0000180a-0000-1000-8000-00805f9b34fb": b"\x00" * 12})
        result = parser.parse(ad)
        assert result is None

    def test_data_too_short(self):
        """Service data shorter than 12 bytes returns None."""
        parser = AmphiroParser()
        ad = _make_ad(service_data={SERVICE_UUID: b"\x00" * 11})
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:amphiro')[:16]."""
        registry = self._registry_and_parser()
        data = _build_service_data(1, 100, 370, 60, 200)
        ad = _make_ad(service_data={SERVICE_UUID: data}, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:amphiro".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex contains the hex-encoded service data."""
        registry = self._registry_and_parser()
        data = _build_service_data(1, 100, 370, 60, 200)
        ad = _make_ad(service_data={SERVICE_UUID: data})
        result = registry.match(ad)[0].parse(ad)

        assert result.raw_payload_hex == data.hex()

    def test_large_session_id(self):
        """Handles large session IDs (uint32 max)."""
        registry = self._registry_and_parser()
        data = _build_service_data(0xFFFFFFFF, 100, 370, 60, 200)
        ad = _make_ad(service_data={SERVICE_UUID: data})
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["session_id"] == 0xFFFFFFFF

    def test_max_uint16_values(self):
        """Handles max uint16 values for volume and temperature."""
        registry = self._registry_and_parser()
        data = _build_service_data(1, 65535, 65535, 65535, 65535)
        ad = _make_ad(service_data={SERVICE_UUID: data})
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["water_volume"] == pytest.approx(6553.5)
        assert result.metadata["water_temperature"] == pytest.approx(6553.5)
        assert result.metadata["duration"] == 65535
        assert result.metadata["energy"] == 65535
