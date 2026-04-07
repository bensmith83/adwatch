"""Tests for TC100 thermocouple/thermometer plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.tc100 import TC100Parser


@pytest.fixture
def parser():
    return TC100Parser()


def make_raw(manufacturer_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


SHORT_MFR = bytes.fromhex("8719f4c1560652fe0026")
LONG_MFR = bytes.fromhex("8719f4c1560652fe0026f4c1560652fe0026")


class TestTC100Parsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result.parser_name == "tc100"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result.beacon_type == "tc100"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result.device_class == "thermometer"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_id(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "52FE"

    def test_long_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=LONG_MFR, service_uuids=["8801", "8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_name_only(self, parser):
        raw = make_raw(local_name="TC100_ABCD")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_id"] == "ABCD"

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"])
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, service_uuids=["8801"], local_name="TC100_52FE")
        result = parser.parse(raw)
        assert result.raw_payload_hex == SHORT_MFR.hex()


class TestTC100Malformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(manufacturer_data=b"\x01\x02\x03\x04")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
