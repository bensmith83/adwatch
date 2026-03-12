"""Tests for Aranet4 CO2 monitor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.aranet4 import Aranet4Parser


ARANET_UUID = "f0cd3001-95da-4f4b-9ac8-aa55d312af0c"


@pytest.fixture
def parser():
    return Aranet4Parser()


def make_raw(service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_uuids=[ARANET_UUID],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


def build_aranet4(co2=450, temp_raw=440, pressure_raw=10130, humidity=55,
                   battery=85, status=0, interval=60, age=15):
    """Build 13-byte Aranet4 payload.

    Default: CO2=450ppm, temp=22.0C (440/20), pressure=1013.0hPa (10130/10),
    humidity=55%, battery=85%, green status, 60s interval, 15s age.
    """
    data = struct.pack("<H", co2)
    data += struct.pack("<H", temp_raw)
    data += struct.pack("<H", pressure_raw)
    data += bytes([humidity, battery, status])
    data += struct.pack("<H", interval)
    data += struct.pack("<H", age)
    return data


NORMAL_DATA = build_aranet4()


class TestAranet4Parsing:
    def test_parse_valid(self, parser):
        raw = make_raw(
            service_data={ARANET_UUID: NORMAL_DATA},
            local_name="Aranet4 12345",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.parser_name == "aranet4"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.beacon_type == "aranet4"

    def test_device_class(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_co2(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["co2_ppm"] == 450

    def test_temperature(self, parser):
        """temp_raw=440 / 20 = 22.0C."""
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.0)

    def test_pressure(self, parser):
        """pressure_raw=10130 / 10 = 1013.0 hPa."""
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["pressure_hpa"] == pytest.approx(1013.0)

    def test_humidity(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == 55

    def test_battery(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["battery"] == 85


class TestAranet4Status:
    def test_status_green(self, parser):
        data = build_aranet4(status=0)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["status"] == "green"

    def test_status_yellow(self, parser):
        data = build_aranet4(status=1)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["status"] == "yellow"

    def test_status_red(self, parser):
        data = build_aranet4(status=2)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["status"] == "red"

    def test_interval(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["interval_s"] == 60

    def test_age(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["age_s"] == 15


class TestAranet4Identity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            service_data={ARANET_UUID: NORMAL_DATA},
            local_name="Aranet4 12345",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66:Aranet4 12345".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestAranet4Malformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None, local_name="Aranet4 12345")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": NORMAL_DATA}, local_name="Aranet4 12345")
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(service_data={ARANET_UUID: bytes(5)}, local_name="Aranet4 12345")
        assert parser.parse(raw) is None
