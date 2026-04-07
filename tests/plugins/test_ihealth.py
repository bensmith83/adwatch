"""Tests for iHealth BLE smart health device plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.ihealth import IHealthParser


@pytest.fixture
def parser():
    return IHealthParser()


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


IHEALTH_MFR = bytes.fromhex("0e020100020002")


class TestIHealthParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert result.parser_name == "ihealth"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert result.beacon_type == "ihealth"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert result.device_class == "health_monitor"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_id(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "000000BAEA9D7A5D9F79"

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"])
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_name_only(self, parser):
        raw = make_raw(local_name="BLESmart_AABBCCDD")
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=IHEALTH_MFR, service_uuids=["fe4a"], local_name="BLESmart_000000BAEA9D7A5D9F79")
        result = parser.parse(raw)
        assert result.raw_payload_hex == IHEALTH_MFR.hex()


class TestIHealthMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(manufacturer_data=b"\x01\x02\x03\x04")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
