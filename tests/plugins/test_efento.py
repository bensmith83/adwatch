"""Tests for Efento environmental sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.efento import EfentoParser


COMPANY_ID = b"\x6C\x02"  # 0x026C little-endian


@pytest.fixture
def parser():
    return EfentoParser()


def make_raw(manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        local_name=None,
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        **defaults,
    )


def build_efento(serial=b"\x01\x02\x03\x04", slots=None, battery=90):
    """Build Efento manufacturer data.

    Format: company_id(2) + version(1) + serial(4) + up to 3 measurement slots + battery(1).
    Each slot: type(1) + value(int16_le)(2).
    """
    data = COMPANY_ID
    data += bytes([0x03])  # version
    data += serial
    if slots is None:
        slots = [(0x01, 225)]  # temp 22.5°C (225/10)
    for sensor_type, value in slots:
        data += bytes([sensor_type])
        data += struct.pack("<h", value)
    data += bytes([battery])
    return data


TEMP_ONLY = build_efento(slots=[(0x01, 225)])
TEMP_HUMIDITY = build_efento(slots=[(0x01, 225), (0x02, 650)])
MULTI_SENSOR = build_efento(slots=[(0x01, 225), (0x02, 650), (0x05, 450)])


class TestEfentoParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result.parser_name == "efento"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result.beacon_type == "efento"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_temperature(self, parser):
        """225 / 10 = 22.5°C."""
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.5)

    def test_serial(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result.metadata["serial"] == "01020304"

    def test_battery(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert result.metadata["battery"] == 90


class TestEfentoMultiSensor:
    def test_temp_and_humidity(self, parser):
        raw = make_raw(manufacturer_data=TEMP_HUMIDITY)
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.5)
        assert result.metadata["humidity"] == pytest.approx(65.0)

    def test_three_sensors(self, parser):
        """Temp + humidity + CO2."""
        raw = make_raw(manufacturer_data=MULTI_SENSOR)
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.5)
        assert result.metadata["humidity"] == pytest.approx(65.0)
        assert result.metadata["co2_ppm"] == 450

    def test_unknown_sensor_type_handled(self, parser):
        """Unknown sensor type should not crash — gracefully skip or label."""
        data = build_efento(slots=[(0x01, 225), (0xFF, 999)])
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(22.5)


class TestEfentoNegativeTemp:
    def test_negative_temperature(self, parser):
        """-50 / 10 = -5.0°C."""
        data = build_efento(slots=[(0x01, -50)])
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-5.0)


class TestEfentoIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=TEMP_ONLY)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_serial(self, parser):
        raw = make_raw(
            manufacturer_data=TEMP_ONLY,
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "11:22:33:44:55:66:01020304".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestEfentoMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID + bytes(2))
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        data = bytearray(TEMP_ONLY)
        data[0] = 0xFF
        data[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(data))
        assert parser.parse(raw) is None
