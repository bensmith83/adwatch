"""Tests for Smart Sensor Devices (BlueBerry) plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.smart_sensor_devices import SmartSensorDevicesParser


COMPANY_ID = 0x075B


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


def _build_mfr_data(sensor_type, value, battery):
    """Build manufacturer_data: company_id(LE) + sensor_type(u8) + value(i16 LE) + battery(u8)."""
    return struct.pack("<HBhB", COMPANY_ID, sensor_type, value, battery)


class TestSmartSensorDevicesParser:
    def _registry_and_parser(self):
        registry = ParserRegistry()

        @register_parser(
            name="smart_sensor_devices",
            company_id=COMPANY_ID,
            description="Smart Sensor Devices BlueBerry sensors",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(SmartSensorDevicesParser):
            pass

        return registry

    def test_match_by_company_id(self):
        """Should match advertisements with company_id 0x075B."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x01, 2350, 85)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_temperature(self):
        """Sensor type 0x01: temperature = value / 100."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x01, 2350, 85)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "smart_sensor_devices"
        assert result.beacon_type == "smart_sensor_devices"
        assert result.device_class == "sensor"
        assert result.metadata["sensor_type"] == "temperature"
        assert result.metadata["value"] == pytest.approx(23.50)
        assert result.metadata["battery"] == 85

    def test_temperature_negative(self):
        """Negative temperature values (int16 signed)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x01, -550, 90)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["sensor_type"] == "temperature"
        assert result.metadata["value"] == pytest.approx(-5.50)

    def test_humidity(self):
        """Sensor type 0x02: humidity = value / 100."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x02, 6500, 70)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["sensor_type"] == "humidity"
        assert result.metadata["value"] == pytest.approx(65.00)
        assert result.metadata["battery"] == 70

    def test_pressure(self):
        """Sensor type 0x03: pressure = value / 10."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x03, 10132, 55)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["sensor_type"] == "pressure"
        assert result.metadata["value"] == pytest.approx(1013.2)
        assert result.metadata["battery"] == 55

    def test_light(self):
        """Sensor type 0x04: light = value (no scaling)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x04, 500, 100)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["sensor_type"] == "light"
        assert result.metadata["value"] == pytest.approx(500.0)
        assert result.metadata["battery"] == 100

    def test_air_quality(self):
        """Sensor type 0x05: air_quality = value (no scaling)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x05, 150, 60)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["sensor_type"] == "air_quality"
        assert result.metadata["value"] == pytest.approx(150.0)
        assert result.metadata["battery"] == 60

    def test_unknown_sensor_type(self):
        """Unknown sensor type should still parse with sensor_type='unknown'."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0xFF, 1234, 42)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["sensor_type"] == "unknown"
        assert result.metadata["value"] == pytest.approx(1234.0)
        assert result.metadata["battery"] == 42

    def test_no_manufacturer_data(self):
        """No manufacturer data returns None."""
        parser = SmartSensorDevicesParser()
        ad = _make_ad(manufacturer_data=None)
        result = parser.parse(ad)
        assert result is None

    def test_too_short_data(self):
        """Manufacturer data too short (< 6 bytes) returns None."""
        parser = SmartSensorDevicesParser()
        ad = _make_ad(manufacturer_data=b"\x5b\x07\x01")
        result = parser.parse(ad)
        assert result is None

    def test_wrong_company_id(self):
        """Wrong company ID returns None."""
        parser = SmartSensorDevicesParser()
        mfr_data = struct.pack("<HBhB", 0xFFFF, 0x01, 2350, 85)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:smart_sensor_devices')[:16]."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x01, 2000, 50)
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:smart_sensor_devices".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_payload_hex(self):
        """raw_payload_hex should contain the payload after company_id."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x01, 2350, 85)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        # payload is bytes after company_id: sensor_type(01) + value(2e09) + battery(55)
        expected_payload = struct.pack("<BhB", 0x01, 2350, 85)
        assert result.raw_payload_hex == expected_payload.hex()
