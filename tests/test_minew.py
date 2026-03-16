"""Tests for Minew industrial BLE beacon plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.minew import MinewParser


COMPANY_ID = 0x0639


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
        name="minew", company_id=COMPANY_ID,
        description="Minew sensors", version="1.0.0", core=False, registry=registry,
    )
    class TestParser(MinewParser):
        pass

    return registry


class TestMinewInfoFrame:
    def test_info_frame_parsed(self):
        """Info frame (0xA1) should parse model, MAC, battery, firmware."""
        registry = _make_registry()
        # payload: frame_type(A1), model(02), MAC(6 bytes), battery(85=85%), firmware(0x0103 = 1.3)
        payload = bytes([0xA1, 0x02]) + bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66]) + bytes([85]) + struct.pack(">H", 0x0103)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "info"
        assert result.metadata["mac"] == "11:22:33:44:55:66"
        assert result.metadata["battery"] == 85
        assert result.metadata["firmware_version"] == "1.3"

    def test_info_frame_identity_hash(self):
        """Identity hash uses MAC from info frame."""
        registry = _make_registry()
        payload = bytes([0xA1, 0x02]) + bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66]) + bytes([85]) + struct.pack(">H", 0x0103)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:minew".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestMinewSensorFrame:
    def test_sensor_frame_positive_temp(self):
        """Sensor frame (0xA2) with positive temperature and humidity."""
        registry = _make_registry()
        # temp = 25.5C -> 25.5 * 256 = 6528 = 0x1980
        # humidity = 60.0% -> 60.0 * 256 = 15360 = 0x3C00
        payload = bytes([0xA2]) + struct.pack(">hH", 6528, 15360)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "sensor"
        assert result.metadata["temperature"] == pytest.approx(25.5)
        assert result.metadata["humidity"] == pytest.approx(60.0)

    def test_sensor_frame_negative_temp(self):
        """Sensor frame with negative temperature."""
        registry = _make_registry()
        # temp = -10.0C -> -10.0 * 256 = -2560
        # humidity = 80.0% -> 80.0 * 256 = 20480
        payload = bytes([0xA2]) + struct.pack(">hH", -2560, 20480)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["temperature"] == pytest.approx(-10.0)
        assert result.metadata["humidity"] == pytest.approx(80.0)

    def test_sensor_frame_identity_uses_ble_mac(self):
        """Sensor frame identity hash uses BLE MAC (no embedded MAC)."""
        registry = _make_registry()
        payload = bytes([0xA2]) + struct.pack(">hH", 6528, 15360)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:minew".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestMinewAccelFrame:
    def test_accel_frame_parsed(self):
        """Accelerometer frame (0xA3) should parse X/Y/Z in milli-g."""
        registry = _make_registry()
        # x=100, y=-200, z=1000
        payload = bytes([0xA3]) + struct.pack(">hhh", 100, -200, 1000)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == "accelerometer"
        assert result.metadata["accel_x"] == 100
        assert result.metadata["accel_y"] == -200
        assert result.metadata["accel_z"] == 1000


class TestMinewEdgeCases:
    def test_unknown_frame_type_returns_none(self):
        """Unknown frame type should return None."""
        registry = _make_registry()
        payload = bytes([0xFF, 0x01, 0x02, 0x03])
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_too_short_data_returns_none(self):
        """Manufacturer data too short should return None."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", COMPANY_ID)  # no payload at all
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_no_manufacturer_data_returns_none(self):
        """No manufacturer data should return None."""
        registry = _make_registry()
        ad = _make_ad()
        # No match at all since no company_id
        matches = registry.match(ad)
        assert len(matches) == 0

    def test_wrong_company_id_returns_none(self):
        """Wrong company ID should return None."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x9999) + bytes([0xA1, 0x02]) + bytes(10)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad) if registry.match(ad) else None
        # might not match at all, or parse returns None
        assert result is None

    def test_truncated_sensor_frame_returns_none(self):
        """Sensor frame with too few bytes should return None."""
        registry = _make_registry()
        payload = bytes([0xA2, 0x19])  # only 1 byte after frame type, need 4
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_truncated_accel_frame_returns_none(self):
        """Accel frame with too few bytes should return None."""
        registry = _make_registry()
        payload = bytes([0xA3, 0x00, 0x01])  # only 2 bytes after frame type, need 6
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_truncated_info_frame_returns_none(self):
        """Info frame with too few bytes should return None."""
        registry = _make_registry()
        payload = bytes([0xA1, 0x02, 0x11])  # only 2 bytes after frame type, need 10
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_parser_name_and_beacon_type(self):
        """ParseResult should have correct parser_name, beacon_type, device_class."""
        registry = _make_registry()
        payload = bytes([0xA2]) + struct.pack(">hH", 6528, 15360)
        mfr_data = struct.pack("<H", COMPANY_ID) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.parser_name == "minew"
        assert result.beacon_type == "minew"
        assert result.device_class == "sensor"
