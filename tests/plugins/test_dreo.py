"""Tests for DREO fan/appliance BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.dreo import DreoParser


@pytest.fixture
def parser():
    return DreoParser()


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


DREO_MFR = bytes.fromhex("4846010003")


class TestDreoParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result.parser_name == "dreo"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result.beacon_type == "dreo"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result.device_class == "fan"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "DREOac03lD9"

    def test_metadata_model_id(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result.metadata["model_id"] == "ac03lD9"

    def test_match_by_name_only(self, parser):
        raw = make_raw(local_name="DREOcd05wA8")
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"])
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=DREO_MFR, service_uuids=["5348"], local_name="DREOac03lD9")
        result = parser.parse(raw)
        assert result.raw_payload_hex == DREO_MFR.hex()


class TestDreoMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(manufacturer_data=b"\x01\x02\x03\x04")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
