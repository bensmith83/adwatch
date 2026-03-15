"""Tests for ELA Innovation industrial BLE sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ela_innovation import ElaInnovationParser


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
        name="ela_innovation",
        company_id=0x0757,
        description="ELA Innovation",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ElaInnovationParser):
        pass

    return registry


def _sensor_mfr_data(temp_raw, humidity_raw, battery, frame_counter=0):
    """Build manufacturer_data for a sensor frame."""
    return (
        struct.pack("<H", 0x0757)  # company ID
        + struct.pack("B", 0x01)   # frame type: sensor
        + struct.pack("B", frame_counter)
        + struct.pack("<h", temp_raw)    # int16 LE temperature * 100
        + struct.pack("<H", humidity_raw)  # uint16 LE humidity * 100
        + struct.pack("B", battery)
    )


def _info_mfr_data(fw_major, fw_minor, hw_major, hw_minor, model_byte, frame_counter=0):
    """Build manufacturer_data for a device info frame."""
    return (
        struct.pack("<H", 0x0757)  # company ID
        + struct.pack("B", 0x02)   # frame type: info
        + struct.pack("B", frame_counter)
        + struct.pack(">H", (fw_major << 8) | fw_minor)  # firmware BE
        + struct.pack(">H", (hw_major << 8) | hw_minor)  # hardware BE
        + struct.pack("B", model_byte)
    )


class TestElaInnovationParser:
    def test_sensor_frame_temp_and_humidity(self):
        """Sensor frame with positive temperature and humidity."""
        registry = _make_registry()
        # temp=23.45C -> raw 2345, humidity=56.78% -> raw 5678, battery=87%
        ad = _make_ad(manufacturer_data=_sensor_mfr_data(2345, 5678, 87, frame_counter=5))
        results = registry.match(ad)
        assert len(results) == 1
        result = results[0].parse(ad)
        assert result is not None
        assert result.parser_name == "ela_innovation"
        assert result.beacon_type == "ela_innovation"
        assert result.device_class == "sensor"
        assert result.metadata["temperature"] == pytest.approx(23.45)
        assert result.metadata["humidity"] == pytest.approx(56.78)
        assert result.metadata["battery"] == 87
        assert result.metadata["frame_counter"] == 5

    def test_sensor_frame_negative_temp(self):
        """Sensor frame with negative temperature (int16 signed)."""
        registry = _make_registry()
        # temp=-10.50C -> raw -1050, humidity=80.00% -> raw 8000, battery=42%
        ad = _make_ad(manufacturer_data=_sensor_mfr_data(-1050, 8000, 42))
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(-10.50)
        assert result.metadata["humidity"] == pytest.approx(80.00)
        assert result.metadata["battery"] == 42

    def test_sensor_frame_zero_humidity(self):
        """Sensor frame with humidity=0 (T-only model) should still include it."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_sensor_mfr_data(2000, 0, 95))
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(20.00)
        assert result.metadata["humidity"] == pytest.approx(0.0)

    def test_info_frame(self):
        """Device info frame should parse firmware, hardware, and model."""
        registry = _make_registry()
        # firmware 2.5, hardware 1.3, model=0x10
        ad = _make_ad(manufacturer_data=_info_mfr_data(2, 5, 1, 3, 0x10, frame_counter=12))
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["firmware_version"] == "2.5"
        assert result.metadata["frame_counter"] == 12
        assert result.metadata["model"] == "0x10"

    def test_unknown_frame_type_returns_none(self):
        """Unknown frame type should return None."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x0757) + b"\xff\x00\x00\x00\x00\x00\x00"
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_too_short_data_returns_none(self):
        """Too-short manufacturer data should return None."""
        registry = _make_registry()
        # Only company ID + frame type, no payload
        mfr_data = struct.pack("<H", 0x0757) + b"\x01"
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:ela_innovation')[:16]."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_sensor_mfr_data(2000, 5000, 50),
            mac_address="11:22:33:44:55:66",
        )
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:ela_innovation".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_manufacturer_data_returns_none(self):
        """No manufacturer data should return None."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=None)
        # No match since no company_id to match on
        assert len(registry.match(ad)) == 0
