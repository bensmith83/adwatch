"""Tests for Mopeka Pro Check tank level sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.mopeka import MopekaParser


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


def _make_mopeka_data(
    hw_id=0x01,
    sensor_type=0x03,
    battery_raw=64,
    temp_raw=65,
    level_raw=500,
    quality_bits=0x03,
    flags=0x00,
    accel_x=None,
    accel_y=None,
):
    """Build Mopeka manufacturer_data bytes."""
    quality_byte = (quality_bits << 6) & 0xFF
    data = struct.pack(
        "<BBBBHBb",
        hw_id,
        sensor_type,
        battery_raw,
        temp_raw,
        level_raw,
        quality_byte,
        flags,
    )
    # struct.pack with "b" for flags makes it signed; use unsigned
    # Rebuild with all unsigned
    data = bytes([hw_id, sensor_type, battery_raw, temp_raw]) + \
           struct.pack("<H", level_raw) + \
           bytes([quality_byte, flags])
    if accel_x is not None and accel_y is not None:
        data += struct.pack("<hh", accel_x, accel_y)
    return data


class TestMopekaMatching:
    def test_match_by_local_name_m_hex(self):
        """Should match local_name starting with M followed by hex chars."""
        registry = ParserRegistry()

        @register_parser(
            name="mopeka", local_name_pattern=r"^M[0-9A-Fa-f]+",
            description="Mopeka", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MopekaParser):
            pass

        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(),
        )
        assert len(registry.match(ad)) == 1

    def test_no_match_without_local_name(self):
        """Should not match without local_name."""
        registry = ParserRegistry()

        @register_parser(
            name="mopeka", local_name_pattern=r"^M[0-9A-Fa-f]+",
            description="Mopeka", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MopekaParser):
            pass

        ad = _make_ad(manufacturer_data=_make_mopeka_data())
        assert len(registry.match(ad)) == 0

    def test_no_match_wrong_local_name(self):
        """Should not match local_name that doesn't start with M+hex."""
        registry = ParserRegistry()

        @register_parser(
            name="mopeka", local_name_pattern=r"^M[0-9A-Fa-f]+",
            description="Mopeka", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MopekaParser):
            pass

        ad = _make_ad(
            local_name="SomeOtherDevice",
            manufacturer_data=_make_mopeka_data(),
        )
        assert len(registry.match(ad)) == 0

    def test_match_lowercase_hex(self):
        """Should match local_name with lowercase hex chars."""
        registry = ParserRegistry()

        @register_parser(
            name="mopeka", local_name_pattern=r"^M[0-9A-Fa-f]+",
            description="Mopeka", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MopekaParser):
            pass

        ad = _make_ad(
            local_name="Mabcdef01",
            manufacturer_data=_make_mopeka_data(),
        )
        assert len(registry.match(ad)) == 1


class TestMopekaParsing:
    def test_parse_pro_check(self):
        """Should parse Pro Check sensor type."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(sensor_type=0x03),
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["sensor_type"] == "pro_check"

    def test_parse_pro_plus(self):
        """Should parse Pro Plus sensor type."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(sensor_type=0x05),
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["sensor_type"] == "pro_plus"

    def test_parse_pro_plus_gen2(self):
        """Should parse Pro Plus Gen2 sensor type."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(sensor_type=0x08),
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["sensor_type"] == "pro_plus_gen2"

    def test_parse_unknown_sensor_type(self):
        """Unknown sensor type should return 'unknown'."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(sensor_type=0xFF),
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["sensor_type"] == "unknown"

    def test_battery_voltage(self):
        """Battery voltage = (raw / 32.0) * 2.0 + 1.5."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(battery_raw=64),
        )
        result = parser.parse(ad)
        expected_voltage = (64 / 32.0) * 2.0 + 1.5  # 5.5V
        assert result.metadata["battery_voltage"] == pytest.approx(expected_voltage)

    def test_temperature(self):
        """Temperature = raw - 40 degrees C."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(temp_raw=65),
        )
        result = parser.parse(ad)
        assert result.metadata["temperature"] == 25.0  # 65 - 40

    def test_temperature_freezing(self):
        """Temperature below zero: raw=30 -> -10C."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(temp_raw=30),
        )
        result = parser.parse(ad)
        assert result.metadata["temperature"] == -10.0

    def test_tank_level_raw(self):
        """Raw level should be uint16 LE time-of-flight in microseconds."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(level_raw=1234),
        )
        result = parser.parse(ad)
        assert result.metadata["tank_level_raw"] == 1234

    def test_quality_high(self):
        """Quality bits 0x03 -> 'high'."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(quality_bits=0x03),
        )
        result = parser.parse(ad)
        assert result.metadata["reading_quality"] == "high"

    def test_quality_medium(self):
        """Quality bits 0x02 -> 'medium'."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(quality_bits=0x02),
        )
        result = parser.parse(ad)
        assert result.metadata["reading_quality"] == "medium"

    def test_quality_low(self):
        """Quality bits 0x01 -> 'low'."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(quality_bits=0x01),
        )
        result = parser.parse(ad)
        assert result.metadata["reading_quality"] == "low"

    def test_quality_no_reading(self):
        """Quality bits 0x00 -> 'no_reading'."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(quality_bits=0x00),
        )
        result = parser.parse(ad)
        assert result.metadata["reading_quality"] == "no_reading"

    def test_sync_pressed(self):
        """Flags bit 0 = sync button pressed."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(flags=0x01),
        )
        result = parser.parse(ad)
        assert result.metadata["sync_pressed"] is True

    def test_sync_not_pressed(self):
        """Flags bit 0 clear = sync not pressed."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(flags=0x00),
        )
        result = parser.parse(ad)
        assert result.metadata["sync_pressed"] is False

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:mopeka')[:16]."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(),
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:mopeka".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_result_fields(self):
        """ParseResult should have correct parser_name, beacon_type, device_class."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=_make_mopeka_data(),
        )
        result = parser.parse(ad)
        assert result.parser_name == "mopeka"
        assert result.beacon_type == "mopeka"
        assert result.device_class == "sensor"

    def test_raw_payload_hex(self):
        """raw_payload_hex should be hex of manufacturer_data."""
        data = _make_mopeka_data()
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=data,
        )
        result = parser.parse(ad)
        assert result.raw_payload_hex == data.hex()


class TestMopekaEdgeCases:
    def test_no_manufacturer_data(self):
        """Should return None if no manufacturer_data."""
        parser = MopekaParser()
        ad = _make_ad(local_name="M1234ABCD", manufacturer_data=None)
        assert parser.parse(ad) is None

    def test_too_short_manufacturer_data(self):
        """Should return None if manufacturer_data < 8 bytes."""
        parser = MopekaParser()
        ad = _make_ad(
            local_name="M1234ABCD",
            manufacturer_data=b"\x01\x03\x40",  # only 3 bytes
        )
        assert parser.parse(ad) is None

    def test_exactly_8_bytes(self):
        """Should parse successfully with exactly 8 bytes (no accel)."""
        parser = MopekaParser()
        data = _make_mopeka_data()
        assert len(data) == 8
        ad = _make_ad(local_name="M1234ABCD", manufacturer_data=data)
        result = parser.parse(ad)
        assert result is not None

    def test_with_accelerometer_data(self):
        """Should parse with optional accelerometer data."""
        parser = MopekaParser()
        data = _make_mopeka_data(flags=0x02, accel_x=100, accel_y=-200)
        assert len(data) == 12
        ad = _make_ad(local_name="M1234ABCD", manufacturer_data=data)
        result = parser.parse(ad)
        assert result is not None
