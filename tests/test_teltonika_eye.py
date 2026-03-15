"""Tests for Teltonika EYE Sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.teltonika_eye import TeltonikEyeParser


COMPANY_ID = 0x089A


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


def _build_mfr_data(flags, sensor_bytes=b""):
    """Build manufacturer_data: company_id(LE) + version(0x01) + flags + sensor_bytes."""
    return struct.pack("<HBB", COMPANY_ID, 0x01, flags) + sensor_bytes


class TestTeltonikEyeParser:
    def _registry_and_parser(self):
        registry = ParserRegistry()

        @register_parser(
            name="teltonika_eye",
            company_id=COMPANY_ID,
            description="Teltonika EYE Sensor",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(TeltonikEyeParser):
            pass

        return registry

    def test_match_by_company_id(self):
        """Should match advertisements with company_id 0x089A."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x00)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_all_flags_set(self):
        """All sensor fields present when flags=0x7F."""
        registry = self._registry_and_parser()
        # temp=2350 (23.50C), humidity=65, magnet=1, movement=100,
        # pitch=-15, roll=45, battery_raw=50 -> 2000+50*10=2500mV
        sensor = (
            struct.pack("<h", 2350)      # temperature int16 LE
            + bytes([65])                 # humidity uint8
            + bytes([1])                  # magnet
            + struct.pack("<H", 100)      # movement uint16 LE
            + struct.pack("<h", -15)      # pitch int16 LE
            + struct.pack("<h", 45)       # roll int16 LE
            + struct.pack("<H", 50)       # battery raw uint16 LE
        )
        mfr_data = _build_mfr_data(0x7F, sensor)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "teltonika_eye"
        assert result.beacon_type == "teltonika_eye"
        assert result.device_class == "sensor"
        assert result.metadata["temperature"] == pytest.approx(23.50)
        assert result.metadata["humidity"] == 65
        assert result.metadata["magnet_detected"] is True
        assert result.metadata["movement_count"] == 100
        assert result.metadata["pitch"] == -15.0
        assert result.metadata["roll"] == 45.0
        assert result.metadata["battery_mv"] == 2500

    def test_partial_flags_temp_humidity(self):
        """Only temperature and humidity (flags=0x03)."""
        registry = self._registry_and_parser()
        sensor = struct.pack("<h", -550) + bytes([82])
        mfr_data = _build_mfr_data(0x03, sensor)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(-5.50)
        assert result.metadata["humidity"] == 82
        assert "magnet_detected" not in result.metadata
        assert "movement_count" not in result.metadata
        assert "battery_mv" not in result.metadata

    def test_partial_flags_battery_only(self):
        """Only battery voltage (flags=0x40)."""
        registry = self._registry_and_parser()
        # raw=80 -> 2000 + 80*10 = 2800 mV
        sensor = struct.pack("<H", 80)
        mfr_data = _build_mfr_data(0x40, sensor)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["battery_mv"] == 2800
        assert "temperature" not in result.metadata

    def test_no_flags(self):
        """No sensor fields (flags=0x00) — still returns ParseResult with empty metadata."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x00)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata == {}

    def test_too_short_data(self):
        """Manufacturer data too short (< 2 bytes) returns None."""
        parser = TeltonikEyeParser()
        ad = _make_ad(manufacturer_data=b"\x9a")
        result = parser.parse(ad)
        assert result is None

    def test_wrong_company_id(self):
        """Wrong company ID returns None."""
        registry = self._registry_and_parser()
        parser = TeltonikEyeParser()
        mfr_data = struct.pack("<HBB", 0xFFFF, 0x01, 0x03) + struct.pack("<h", 2000) + bytes([50])
        ad = _make_ad(manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result is None

    def test_no_manufacturer_data(self):
        """No manufacturer data returns None."""
        parser = TeltonikEyeParser()
        ad = _make_ad(manufacturer_data=None)
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:teltonika_eye')[:16]."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x00)
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:teltonika_eye".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_magnet_not_detected(self):
        """Magnet field value 0 → False."""
        registry = self._registry_and_parser()
        sensor = bytes([0])  # magnet=0
        mfr_data = _build_mfr_data(0x04, sensor)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["magnet_detected"] is False

    def test_negative_pitch_roll(self):
        """Negative pitch and roll angles."""
        registry = self._registry_and_parser()
        # flags=0x30 (pitch + roll)
        sensor = struct.pack("<h", -90) + struct.pack("<h", -180)
        mfr_data = _build_mfr_data(0x30, sensor)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["pitch"] == -90.0
        assert result.metadata["roll"] == -180.0

    def test_payload_too_short_for_flags(self):
        """If flags indicate fields but payload is truncated, returns None."""
        registry = self._registry_and_parser()
        # flags=0x01 (temperature needs 2 bytes) but no sensor bytes
        mfr_data = _build_mfr_data(0x01)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None
