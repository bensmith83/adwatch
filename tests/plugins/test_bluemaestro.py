"""Tests for BlueMaestro Tempo Disc plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.bluemaestro import BlueMaestroParser


COMPANY_ID = b"\x33\x01"  # 0x0133 little-endian


@pytest.fixture
def parser():
    return BlueMaestroParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


def build_bluemaestro(version=3, battery=85, temp=225, humidity=650,
                       dewpoint=140, max_temp=280, min_temp=180,
                       max_hum=750, min_hum=500, interval=300):
    """Build 20-byte BlueMaestro manufacturer data (company_id + 18 payload).

    Default: temp=22.5C (225/10), humidity=65.0% (650/10), dewpoint=14.0C.
    All int16 values are signed for temps, unsigned for humidity.
    """
    data = COMPANY_ID
    data += bytes([version, battery])
    data += struct.pack(">h", temp)       # current temp (signed)
    data += struct.pack(">H", humidity)   # current humidity
    data += struct.pack(">h", dewpoint)   # dew point (signed)
    data += struct.pack(">h", max_temp)
    data += struct.pack(">h", min_temp)
    data += struct.pack(">H", max_hum)
    data += struct.pack(">H", min_hum)
    data += struct.pack(">H", interval)
    return data


NORMAL_DATA = build_bluemaestro()


class TestBlueMaestroParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.parser_name == "bluemaestro"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.beacon_type == "bluemaestro"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_temperature(self, parser):
        """225 / 10 = 22.5C."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.5)

    def test_humidity(self, parser):
        """650 / 10 = 65.0%."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.0)

    def test_dewpoint(self, parser):
        """140 / 10 = 14.0C."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["dewpoint_c"] == pytest.approx(14.0)

    def test_battery(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["battery"] == 85

    def test_interval(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["interval_s"] == 300


class TestBlueMaestroNegativeTemp:
    def test_negative_temperature(self, parser):
        """-50 / 10 = -5.0C."""
        data = build_bluemaestro(temp=-50)
        raw = make_raw(manufacturer_data=data, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-5.0)

    def test_negative_dewpoint(self, parser):
        data = build_bluemaestro(dewpoint=-30)
        raw = make_raw(manufacturer_data=data, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["dewpoint_c"] == pytest.approx(-3.0)


class TestBlueMaestroMinMax:
    def test_max_temperature(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["max_temp_c"] == pytest.approx(28.0)

    def test_min_temperature(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["min_temp_c"] == pytest.approx(18.0)

    def test_max_humidity(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["max_humidity"] == pytest.approx(75.0)

    def test_min_humidity(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert result.metadata["min_humidity"] == pytest.approx(50.0)


class TestBlueMaestroIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="T30")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            manufacturer_data=NORMAL_DATA,
            local_name="T30",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66:T30".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestBlueMaestroMatching:
    def test_matches_td_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TD20")
        result = parser.parse(raw)
        assert result is not None


class TestBlueMaestroMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="T30")
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID + bytes(4), local_name="T30")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        data = bytearray(NORMAL_DATA)
        data[0] = 0xFF
        data[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(data), local_name="T30")
        assert parser.parse(raw) is None
