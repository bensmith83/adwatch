"""Tests for ATC/PVVX custom firmware thermometer plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.atc_pvvx import AtcPvvxParser


SVC_UUID = "181a"


@pytest.fixture
def parser():
    return AtcPvvxParser()


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


def build_atc(mac=None, temp_raw=2250, humidity_raw=6500, battery_mv=3100,
               battery_pct=85, counter=42, flags=0):
    """Build 13-byte ATC1.1 format service data (big-endian).

    Default: temp=22.50C (2250/100), humidity=65.00% (6500/100).
    """
    if mac is None:
        mac = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
    data = mac
    data += struct.pack(">h", temp_raw)      # int16 BE
    data += struct.pack(">H", humidity_raw)   # uint16 BE
    data += struct.pack(">H", battery_mv)     # uint16 BE
    data += bytes([battery_pct, counter, flags])
    return data


def build_pvvx(mac=None, temp_raw=2250, humidity_raw=6500, battery_mv=3100,
                battery_pct=85, counter=42, flags=0, trigger=b"\x00\x00"):
    """Build 18-byte PVVX extended format service data (little-endian).

    Default: temp=22.50C (2250/100), humidity=65.00% (6500/100).
    """
    if mac is None:
        mac = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
    data = mac
    data += struct.pack("<h", temp_raw)      # int16 LE
    data += struct.pack("<H", humidity_raw)   # uint16 LE
    data += struct.pack("<H", battery_mv)     # uint16 LE
    data += bytes([battery_pct, counter, flags, 0x00])  # +reserved byte
    data += trigger
    return data


ATC_DATA = build_atc()
PVVX_DATA = build_pvvx()


class TestAtcParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.parser_name == "atc_pvvx"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.beacon_type == "atc_pvvx"

    def test_device_class(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_temperature(self, parser):
        """2250 / 100 = 22.50C."""
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.50)

    def test_humidity(self, parser):
        """6500 / 100 = 65.00%."""
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.00)

    def test_battery_mv(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["battery_mv"] == 3100

    def test_battery_pct(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["battery_pct"] == 85

    def test_format_detected_atc(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["format"] == "atc"


class TestAtcNegativeTemp:
    def test_negative_temperature(self, parser):
        """-500 / 100 = -5.0C."""
        data = build_atc(temp_raw=-500)
        raw = make_raw(service_data={SVC_UUID: data}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-5.0)


class TestPvvxParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_data={SVC_UUID: PVVX_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result is not None

    def test_format_detected_pvvx(self, parser):
        raw = make_raw(service_data={SVC_UUID: PVVX_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["format"] == "pvvx"

    def test_temperature_pvvx(self, parser):
        """Same value, little-endian encoding."""
        raw = make_raw(service_data={SVC_UUID: PVVX_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.50)

    def test_humidity_pvvx(self, parser):
        raw = make_raw(service_data={SVC_UUID: PVVX_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.00)

    def test_battery_mv_pvvx(self, parser):
        raw = make_raw(service_data={SVC_UUID: PVVX_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert result.metadata["battery_mv"] == 3100


class TestAtcPvvxIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={SVC_UUID: ATC_DATA}, local_name="ATC_AABBCC")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            service_data={SVC_UUID: ATC_DATA},
            local_name="ATC_AABBCC",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66:ATC_AABBCC".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestAtcPvvxMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None, local_name="ATC_AABBCC")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": ATC_DATA}, local_name="ATC_AABBCC")
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(service_data={SVC_UUID: bytes(5)}, local_name="ATC_AABBCC")
        assert parser.parse(raw) is None
