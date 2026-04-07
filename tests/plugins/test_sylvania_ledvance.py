"""Tests for Sylvania/LEDVANCE smart light plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.sylvania_ledvance import SylvaniaLedvanceParser


@pytest.fixture
def parser():
    return SylvaniaLedvanceParser()


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


SIL_MFR = bytes.fromhex("19088a6c170000000000c2")
DUE_MFR = bytes.fromhex("1908116009400b000000c2")


class TestSylvaniaLedvanceParsing:
    def test_parse_sil_device(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result.parser_name == "sylvania_ledvance"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result.beacon_type == "sylvania_ledvance"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result.device_class == "smart_light"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_id(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "4914"

    def test_metadata_brand_sil(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result.metadata["brand"] == "Sylvania"

    def test_due_brand(self, parser):
        raw = make_raw(manufacturer_data=DUE_MFR, service_uuids=["fdc1"], local_name="DUE:1568")
        result = parser.parse(raw)
        assert result.metadata["brand"] == "LEDVANCE"

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"])
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_name_only(self, parser):
        raw = make_raw(local_name="SIL:ABCD")
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=SIL_MFR, service_uuids=["fdc1"], local_name="SIL:4914")
        result = parser.parse(raw)
        assert result.raw_payload_hex == SIL_MFR.hex()


class TestSylvaniaLedvanceMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(manufacturer_data=b"\x01\x02\x03\x04")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
