"""Tests for SensorPush plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.sensorpush import SensorPushParser


@pytest.fixture
def parser():
    return SensorPushParser()


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


def build_sensorpush(temp_raw=2250, humidity_raw=6500):
    """Build SensorPush manufacturer data.

    Format: company_id(2) + temp(int16_le, /100 °C) + humidity(uint16_le, /100 %).
    Default: 22.50°C, 65.00%.
    """
    data = b"\x00\x00"  # placeholder company ID bytes
    data += struct.pack("<h", temp_raw)
    data += struct.pack("<H", humidity_raw)
    return data


NORMAL_DATA = build_sensorpush()


class TestSensorPushParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result.parser_name == "sensorpush"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result.beacon_type == "sensorpush"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_temperature(self, parser):
        """2250 / 100 = 22.50°C."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.50)

    def test_humidity(self, parser):
        """6500 / 100 = 65.00%."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.00)

    def test_negative_temperature(self, parser):
        data = build_sensorpush(temp_raw=-500)
        raw = make_raw(manufacturer_data=data, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-5.0)


class TestSensorPushMatching:
    def test_matches_ht_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT 5678")
        result = parser.parse(raw)
        assert result is not None

    def test_matches_htp_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HTP.xw AB12")
        result = parser.parse(raw)
        assert result is not None

    def test_rejects_without_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name=None)
        assert parser.parse(raw) is None

    def test_rejects_wrong_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="OtherDevice")
        assert parser.parse(raw) is None


class TestSensorPushIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SensorPush HT.w 1234")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            manufacturer_data=NORMAL_DATA,
            local_name="SensorPush HT.w 1234",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "11:22:33:44:55:66:SensorPush HT.w 1234".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestSensorPushMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="SensorPush HT.w 1234")
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=b"\x00\x00", local_name="SensorPush HT.w 1234")
        assert parser.parse(raw) is None
