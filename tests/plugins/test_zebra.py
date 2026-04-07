"""Tests for Zebra Technologies barcode scanner plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.zebra import ZebraParser


@pytest.fixture
def parser():
    return ZebraParser()


def make_raw(service_uuids=None, local_name=None, manufacturer_data=None, service_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


class TestZebraParsing:
    def test_parse_by_service_uuid(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result.parser_name == "zebra"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result.beacon_type == "zebra"

    def test_device_class(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result.device_class == "barcode_scanner"

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            service_uuids=["fe79"],
            local_name="096_PDZebra1",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("zebra:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_store_number_extracted(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result.metadata["store_number"] == "096"

    def test_department_code_pd(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result.metadata["department_code"] == "PD"
        assert result.metadata["department"] == "Produce"

    def test_department_code_pharm(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PharmZebra")
        result = parser.parse(raw)
        assert result.metadata["department_code"] == "Pharm"
        assert result.metadata["department"] == "Pharmacy"

    def test_department_code_ca(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_CA_CAC")
        result = parser.parse(raw)
        assert result.metadata["department_code"] == "CA"
        assert result.metadata["department"] == "Checkout Area"

    def test_device_name_extracted(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_PDZebra1")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Zebra1"

    def test_device_name_floral(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_CA_Floral")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Floral"

    def test_unknown_department(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="096_XY_Device1")
        result = parser.parse(raw)
        assert result.metadata["department_code"] == "XY"
        assert result.metadata["department"] == "Unknown"

    def test_no_name_still_parses(self, parser):
        raw = make_raw(service_uuids=["fe79"])
        result = parser.parse(raw)
        assert result is not None
        assert "store_number" not in result.metadata

    def test_name_without_store_pattern(self, parser):
        raw = make_raw(service_uuids=["fe79"], local_name="SomeZebraDevice")
        result = parser.parse(raw)
        assert result is not None
        assert "store_number" not in result.metadata


class TestZebraMalformed:
    def test_returns_none_no_service_uuid(self, parser):
        raw = make_raw(service_uuids=[], local_name="096_PDZebra1")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_service_uuid(self, parser):
        raw = make_raw(service_uuids=["fe78"], local_name="096_PDZebra1")
        assert parser.parse(raw) is None


class TestZebraPluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Zebra"
