"""Tests for Hatch baby sound machine / night light plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.hatch import HatchParser


@pytest.fixture
def parser():
    return HatchParser()


# Realistic 50-byte manufacturer_data: company_id 0x0434 (LE) + 48 bytes payload
SAMPLE_PAYLOAD = bytes(48)
SAMPLE_MFR_DATA = bytes.fromhex("3404") + SAMPLE_PAYLOAD


def make_raw(**kwargs):
    defaults = dict(
        timestamp="2026-03-07T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=SAMPLE_MFR_DATA,
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


class TestHatchParsing:
    def test_parse_valid(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.parser_name == "hatch"

    def test_beacon_type(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.beacon_type == "hatch"

    def test_device_class(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.device_class == "smart_home"

    def test_identity_hash_value(self, parser):
        raw = make_raw(mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_raw_payload_hex(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.raw_payload_hex == SAMPLE_PAYLOAD.hex()

    def test_metadata_payload_hex(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == SAMPLE_PAYLOAD.hex()

    def test_metadata_payload_length(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == 48

    def test_battery_level_from_service_data(self, parser):
        raw = make_raw(service_data={"180f": b"\x64"})
        result = parser.parse(raw)
        assert result.metadata["battery_level"] == 100

    def test_battery_level_other_value(self, parser):
        raw = make_raw(service_data={"180f": b"\x32"})
        result = parser.parse(raw)
        assert result.metadata["battery_level"] == 50

    def test_no_battery_without_service_data(self, parser):
        raw = make_raw(service_data=None)
        result = parser.parse(raw)
        assert "battery_level" not in result.metadata

    def test_device_name_from_local_name(self, parser):
        raw = make_raw(local_name="Bedroom Hatch")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Bedroom Hatch"

    def test_no_device_name_without_local_name(self, parser):
        raw = make_raw(local_name=None)
        result = parser.parse(raw)
        assert "device_name" not in result.metadata


class TestHatchMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        # Company ID 0xFFFF instead of 0x0434
        raw = make_raw(manufacturer_data=bytes.fromhex("FFFF") + bytes(48))
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("3404"))
        assert parser.parse(raw) is None


class TestHatchMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Hatch"
