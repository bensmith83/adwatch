"""Tests for Clover payment terminal plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.clover import CloverParser


@pytest.fixture
def parser():
    return CloverParser()


def make_raw(manufacturer_data=None, service_data=None, service_uuids=None, local_name=None, **kwargs):
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


# Full Clover mfr data with ASCII serial
CLOVER_MFR_FULL = bytes.fromhex("71030104620002004a424855333436343237")
CLOVER_MFR_SHORT = bytes.fromhex("710301044b00")


class TestCloverParsing:
    def test_parse_valid_data(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.parser_name == "clover"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.beacon_type == "clover"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.device_class == "payment_terminal"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            manufacturer_data=CLOVER_MFR_FULL,
            local_name="CCJB621450531",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("clover:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_model_code_jb(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.metadata["model_code"] == "JB"
        assert result.metadata["model"] == "Clover Flex"

    def test_model_code_gb(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_SHORT, local_name="CCGB616512155")
        result = parser.parse(raw)
        assert result.metadata["model_code"] == "GB"
        assert result.metadata["model"] == "Clover Go"

    def test_local_serial(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.metadata["local_serial"] == "621450531"

    def test_hardware_serial_extracted(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.metadata["hardware_serial"] == "JBHU346427"

    def test_no_hardware_serial_short_payload(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_SHORT, local_name="CCGB616512155")
        result = parser.parse(raw)
        assert "hardware_serial" not in result.metadata

    def test_protocol_version(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCJB621450531")
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == 1

    def test_no_local_name(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL)
        result = parser.parse(raw)
        assert result is not None
        assert "model_code" not in result.metadata

    def test_unknown_model_code(self, parser):
        raw = make_raw(manufacturer_data=CLOVER_MFR_FULL, local_name="CCXX999999999")
        result = parser.parse(raw)
        assert result.metadata["model_code"] == "XX"
        assert result.metadata["model"] == "Unknown"


class TestCloverMalformed:
    def test_returns_none_no_mfr_data(self, parser):
        raw = make_raw(local_name="CCJB621450531")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c000104620002004a42"))
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("7103"))
        assert parser.parse(raw) is None


class TestCloverPluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Clover"
