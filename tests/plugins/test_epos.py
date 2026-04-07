"""Tests for EPOS audio device plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.epos import EposParser


@pytest.fixture
def parser():
    return EposParser()


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


EPOS_MFR_DATA = bytes.fromhex("820060bf74941600")
EPOS_PAYLOAD = bytes.fromhex("60bf74941600")


class TestEposParsing:
    def test_parse_valid_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.parser_name == "epos"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.beacon_type == "epos"

    def test_device_class_audio(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.device_class == "audio"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            manufacturer_data=EPOS_MFR_DATA,
            local_name="EPOS EXPAND 40",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("epos:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_model_name_extracted(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.metadata["model"] == "EXPAND 40"

    def test_device_id_bytes(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "7494"

    def test_protocol_version(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == "1600"

    def test_state_bytes(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.metadata["state_hex"] == "60bf"

    def test_different_state_bytes(self, parser):
        data = bytes.fromhex("8200e0c074941600")
        raw = make_raw(manufacturer_data=data, local_name="EPOS EXPAND 40")
        result = parser.parse(raw)
        assert result.metadata["state_hex"] == "e0c0"

    def test_no_local_name(self, parser):
        raw = make_raw(manufacturer_data=EPOS_MFR_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert "model" not in result.metadata


class TestEposMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="EPOS EXPAND 40")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c0060bf74941600"))
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("8200"))
        assert parser.parse(raw) is None


class TestEposPluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "EPOS"
