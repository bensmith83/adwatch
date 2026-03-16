"""Tests for MikroTik BLE Tag asset tracking plugin."""

import hashlib
import math
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.mikrotik_tag import MikroTikTagParser


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


def _build_mfr_data(version=1, flags=0x04, mac=b"\x11\x22\x33\x44\x55\x66",
                     accel_x=0, accel_y=0, accel_z=1000,
                     temp_raw=6400, uptime=300, battery=85):
    """Build manufacturer_data for MikroTik custom format."""
    data = struct.pack("BB", version, flags)
    if flags & 0x04:  # MAC included
        data += mac
    data += struct.pack("<hhh", accel_x, accel_y, accel_z)
    data += struct.pack("<hHB", temp_raw, uptime, battery)
    return data


def _register(registry):
    @register_parser(
        name="mikrotik_tag",
        local_name_pattern=r"^MikroTik",
        description="MikroTik BLE Tag",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(MikroTikTagParser):
        pass
    return TestParser


class TestMikroTikTagParser:
    def test_match_by_local_name(self):
        """Should match advertisements with local_name starting with 'MikroTik'."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(
            local_name="MikroTik TG-BT5-IN",
            manufacturer_data=_build_mfr_data(),
        )
        assert len(registry.match(ad)) == 1

    def test_no_match_wrong_name(self):
        """Should not match if local_name doesn't start with MikroTik."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(
            local_name="SomeOtherDevice",
            manufacturer_data=_build_mfr_data(),
        )
        assert len(registry.match(ad)) == 0

    def test_parse_unencrypted_with_mac(self):
        """Parse unencrypted payload with MAC included (flags=0x04)."""
        registry = ParserRegistry()
        _register(registry)

        mfr = _build_mfr_data(
            version=1, flags=0x04,
            mac=b"\x11\x22\x33\x44\x55\x66",
            accel_x=100, accel_y=-200, accel_z=980,
            temp_raw=6400, uptime=300, battery=85,
        )
        ad = _make_ad(
            local_name="MikroTik TG-BT5-IN",
            manufacturer_data=mfr,
        )
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "mikrotik_tag"
        assert result.device_class == "tracker"
        assert result.metadata["accel_x"] == 100
        assert result.metadata["accel_y"] == -200
        assert result.metadata["accel_z"] == 980
        assert result.metadata["temperature"] == 25.0  # 6400/256
        assert result.metadata["uptime"] == 300
        assert result.metadata["battery"] == 85
        assert result.metadata["encrypted"] is False

    def test_parse_unencrypted_without_mac(self):
        """Parse unencrypted payload without MAC (flags=0x00)."""
        registry = ParserRegistry()
        _register(registry)

        # No MAC: flags=0x00, sensor data starts at byte 2
        mfr = _build_mfr_data(
            version=1, flags=0x00,
            accel_x=0, accel_y=0, accel_z=1000,
            temp_raw=5120, uptime=600, battery=50,
        )
        ad = _make_ad(
            local_name="MikroTik TG-BT5-OUT",
            manufacturer_data=mfr,
        )
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["accel_x"] == 0
        assert result.metadata["accel_y"] == 0
        assert result.metadata["accel_z"] == 1000
        assert result.metadata["temperature"] == 20.0  # 5120/256
        assert result.metadata["uptime"] == 600
        assert result.metadata["battery"] == 50

    def test_encrypted_payload(self):
        """Encrypted payload (flags bit 0 set) returns encrypted=True, no sensor data."""
        registry = ParserRegistry()
        _register(registry)

        # flags=0x05 (encrypted + MAC included), payload after MAC is encrypted
        data = struct.pack("BB", 1, 0x05)
        data += b"\x11\x22\x33\x44\x55\x66"  # MAC
        data += b"\x00" * 11  # encrypted junk
        ad = _make_ad(
            local_name="MikroTik TG-BT5-IN",
            manufacturer_data=data,
        )
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["encrypted"] is True
        assert "accel_x" not in result.metadata
        assert "temperature" not in result.metadata

    def test_tilt_angle_calculation(self):
        """Tilt angle should be calculated from accelerometer data."""
        registry = ParserRegistry()
        _register(registry)

        # Upright: x=0, y=0, z=1000 → tilt ≈ 0°
        mfr = _build_mfr_data(accel_x=0, accel_y=0, accel_z=1000)
        ad = _make_ad(local_name="MikroTik TG-BT5-IN", manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["tilt_angle"] == 0.0

        # Tilted 45°: x=707, y=0, z=707
        mfr2 = _build_mfr_data(accel_x=707, accel_y=0, accel_z=707)
        ad2 = _make_ad(local_name="MikroTik TG-BT5-IN", manufacturer_data=mfr2)
        result2 = registry.match(ad2)[0].parse(ad2)
        assert abs(result2.metadata["tilt_angle"] - 45.0) < 0.1

    def test_tilt_angle_flat(self):
        """Flat on side: x=1000, y=0, z=0 → tilt ≈ 90°."""
        registry = ParserRegistry()
        _register(registry)

        mfr = _build_mfr_data(accel_x=1000, accel_y=0, accel_z=0)
        ad = _make_ad(local_name="MikroTik TG-BT5-IN", manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["tilt_angle"] == 90.0

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:mikrotik_tag')[:16]."""
        registry = ParserRegistry()
        _register(registry)

        mfr = _build_mfr_data()
        ad = _make_ad(
            local_name="MikroTik TG-BT5-IN",
            manufacturer_data=mfr,
            mac_address="11:22:33:44:55:66",
        )
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:mikrotik_tag".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_too_short_data(self):
        """Too-short manufacturer_data should return None."""
        registry = ParserRegistry()
        _register(registry)

        ad = _make_ad(
            local_name="MikroTik TG-BT5-IN",
            manufacturer_data=b"\x01",  # only 1 byte
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_no_manufacturer_data(self):
        """No manufacturer_data should return None."""
        registry = ParserRegistry()
        _register(registry)

        ad = _make_ad(local_name="MikroTik TG-BT5-IN", manufacturer_data=None)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_negative_temperature(self):
        """Negative temperature should be handled correctly."""
        registry = ParserRegistry()
        _register(registry)

        # -10°C = -2560 as int16
        mfr = _build_mfr_data(temp_raw=-2560)
        ad = _make_ad(local_name="MikroTik TG-BT5-IN", manufacturer_data=mfr)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["temperature"] == -10.0
