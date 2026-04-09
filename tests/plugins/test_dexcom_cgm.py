"""Tests for Dexcom CGM plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.dexcom_cgm import DexcomCgmParser


@pytest.fixture
def parser():
    return DexcomCgmParser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-09T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


DEXCOM_UUID = "61ce1c20-e8bc-4287-91fd-7cc25f0df500"
DEVICE_INFO_UUID = "180a"


class TestDexcomCgmParsing:
    def test_parse_by_service_uuid(self, parser):
        raw = make_raw(service_uuids=[DEVICE_INFO_UUID, DEXCOM_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_by_name_dex(self, parser):
        raw = make_raw(local_name="DEX", service_uuids=[DEVICE_INFO_UUID, DEXCOM_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parse_by_name_dexcom(self, parser):
        raw = make_raw(local_name="Dexcom1A", service_uuids=[DEXCOM_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert result.parser_name == "dexcom_cgm"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert result.beacon_type == "dexcom_cgm"

    def test_device_class_medical(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert result.device_class == "medical"

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            service_uuids=[DEXCOM_UUID],
            local_name="DEX",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_metadata_device_name(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "DEX"

    def test_metadata_model_g7(self, parser):
        """G7 transmitters use short names like DEX."""
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert "model" in result.metadata

    def test_no_match_unrelated(self, parser):
        raw = make_raw(service_uuids=["1234"], local_name="SomeDevice")
        result = parser.parse(raw)
        assert result is None

    def test_no_match_empty(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result is None

    def test_has_device_info_flag(self, parser):
        raw = make_raw(
            service_uuids=[DEVICE_INFO_UUID, DEXCOM_UUID], local_name="DEX"
        )
        result = parser.parse(raw)
        assert result.metadata.get("has_device_info") is True

    def test_no_device_info_flag(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_UUID], local_name="DEX")
        result = parser.parse(raw)
        assert result.metadata.get("has_device_info") is not True
