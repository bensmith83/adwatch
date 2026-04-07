"""Tests for Samsung appliance BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.samsung_appliance import SamsungApplianceParser


@pytest.fixture
def parser():
    return SamsungApplianceParser()


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


FRIDGE_MFR = bytes.fromhex("7500420c83455d30414a54524531000104a457a04da6020a02043631395604020400")
TV_MFR = bytes.fromhex("7500021834a14fa4deff26093f21e7a359d642da6e7f9289")


class TestSamsungApplianceParsing:
    def test_parse_fridge(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert result.parser_name == "samsung_appliance"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert result.beacon_type == "samsung_appliance"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Refrigerato"

    def test_match_by_company_id_only(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR)
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=FRIDGE_MFR, local_name="Refrigerato")
        result = parser.parse(raw)
        assert result.raw_payload_hex == FRIDGE_MFR.hex()


class TestSamsungApplianceMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(manufacturer_data=b"\x01\x02\x03\x04")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company(self, parser):
        raw = make_raw(manufacturer_data=b"\x99\x99\x01\x02")
        assert parser.parse(raw) is None
