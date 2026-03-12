"""Tests for Sensirion MyCO2/MyAmbience gadget plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.sensirion import SensirionParser


SVC_UUID = "fe40"


@pytest.fixture
def parser():
    return SensirionParser()


def make_raw(service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_uuids=[SVC_UUID],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


def build_sensirion(device_type=0x01, temp_raw=2250, humidity_raw=6500, co2=None):
    """Build Sensirion service data.

    Format: device_type(1) + temp(int16_le, /100 °C) + humidity(uint16_le, /100 %) + optional co2(uint16_le).
    Default: type=1, 22.50°C, 65.00%.
    """
    data = bytes([device_type])
    data += struct.pack("<h", temp_raw)
    data += struct.pack("<H", humidity_raw)
    if co2 is not None:
        data += struct.pack("<H", co2)
    return data


TEMP_HUM_DATA = build_sensirion()
TEMP_HUM_CO2_DATA = build_sensirion(co2=850)


class TestSensirionParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "sensirion"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "sensirion"

    def test_device_class(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_temperature(self, parser):
        """2250 / 100 = 22.50°C."""
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.50)

    def test_humidity(self, parser):
        """6500 / 100 = 65.00%."""
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.00)

    def test_device_type(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert result.metadata["device_type"] == 0x01


class TestSensirionWithCO2:
    def test_co2_present(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_CO2_DATA})
        result = parser.parse(raw)
        assert result.metadata["co2_ppm"] == 850

    def test_co2_absent(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert "co2_ppm" not in result.metadata


class TestSensirionIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={SVC_UUID: TEMP_HUM_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            service_data={SVC_UUID: TEMP_HUM_DATA},
            local_name="MyCO2",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "11:22:33:44:55:66:MyCO2".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestSensirionMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": TEMP_HUM_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(service_data={SVC_UUID: bytes(2)})
        assert parser.parse(raw) is None
