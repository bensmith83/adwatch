"""Tests for ThermoBeacon plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.thermobeacon import ThermoBeaconParser


COMPANY_ID = b"\x11\x00"  # 0x0011 little-endian


@pytest.fixture
def parser():
    return ThermoBeaconParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


def build_thermobeacon(temp_raw=352, humidity_raw=800, battery_mv=3100, mac=None, uptime=None):
    """Build 18-byte ThermoBeacon manufacturer data.

    Default: temp=22.0C (352/16), humidity=50.0% (800/16), battery=3100mV.
    """
    if mac is None:
        mac = bytes([0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA])  # reversed
    if uptime is None:
        uptime = bytes(6)
    data = COMPANY_ID + mac
    data += struct.pack("<H", temp_raw)
    data += struct.pack("<H", humidity_raw)
    data += struct.pack("<H", battery_mv)
    data += uptime
    return data


NORMAL_DATA = build_thermobeacon()


class TestThermoBeaconParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result.parser_name == "thermobeacon"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result.beacon_type == "thermobeacon"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_temperature_normal(self, parser):
        """temp_raw=352 / 16 = 22.0C."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.0)

    def test_humidity(self, parser):
        """humidity_raw=800 / 16 = 50.0%."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(50.0)

    def test_battery_mv(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert result.metadata["battery_mv"] == 3100


class TestThermoBeaconNegativeTemp:
    def test_negative_temperature(self, parser):
        """temp_raw > 4000 means negative: 4080 - 4096 = -16, /16 = -1.0C."""
        data = build_thermobeacon(temp_raw=4080)
        raw = make_raw(manufacturer_data=data, local_name="TP357")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-1.0)

    def test_very_negative_temperature(self, parser):
        """temp_raw=4001 → 4001-4096=-95 → -95/16 = -5.9375C."""
        data = build_thermobeacon(temp_raw=4001)
        raw = make_raw(manufacturer_data=data, local_name="TP357")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-5.9375)

    def test_zero_temperature(self, parser):
        """temp_raw=0 → 0/16 = 0.0C."""
        data = build_thermobeacon(temp_raw=0)
        raw = make_raw(manufacturer_data=data, local_name="TP357")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(0.0)


class TestThermoBeaconIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            manufacturer_data=NORMAL_DATA,
            local_name="TP357",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66:TP357".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestThermoBeaconMatching:
    def test_matches_lanyard_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Lanyard")
        result = parser.parse(raw)
        assert result is not None

    def test_matches_tp_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="TP358")
        result = parser.parse(raw)
        assert result is not None


class TestThermoBeaconMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="TP357")
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID + bytes(4), local_name="TP357")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        data = bytearray(NORMAL_DATA)
        data[0] = 0xFF
        data[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(data), local_name="TP357")
        assert parser.parse(raw) is None
