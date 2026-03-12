"""Tests for Bose audio device plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.bose import BoseParser


@pytest.fixture
def parser():
    return BoseParser()


def make_raw(manufacturer_data=None, service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-07T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


# Realistic sample: company_id 0x0065 LE = 0x65, 0x00, then payload 0x01, 0xc9, 0x01
BOSE_MFR_DATA = bytes.fromhex("650001c901")
BOSE_PAYLOAD = bytes.fromhex("01c901")

FDF7_SERVICE_DATA = bytes(range(36))


class TestBoseParsing:
    def test_parse_valid_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result.parser_name == "bose"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result.beacon_type == "bose"

    def test_device_class_audio(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result.device_class == "audio"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_identity_hash_value(self, parser):
        """Identity = SHA256(mac_address)[:16]."""
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA, mac_address="11:22:33:44:55:66")
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result.raw_payload_hex == BOSE_PAYLOAD.hex()

    def test_metadata_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == BOSE_PAYLOAD.hex()

    def test_metadata_payload_length(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == len(BOSE_PAYLOAD)

    def test_metadata_no_service_data_by_default(self, parser):
        raw = make_raw(manufacturer_data=BOSE_MFR_DATA)
        result = parser.parse(raw)
        assert "service_payload_hex" not in result.metadata

    def test_metadata_with_fdf7_service_data(self, parser):
        raw = make_raw(
            manufacturer_data=BOSE_MFR_DATA,
            service_data={"fdf7": FDF7_SERVICE_DATA},
        )
        result = parser.parse(raw)
        assert result.metadata["service_payload_hex"] == FDF7_SERVICE_DATA.hex()
        assert result.metadata["service_payload_length"] == len(FDF7_SERVICE_DATA)


class TestBoseMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        # Company ID 0x004C (Apple) instead of 0x0065 (Bose)
        raw = make_raw(manufacturer_data=bytes.fromhex("4c0001c901"))
        assert parser.parse(raw) is None

    def test_returns_none_empty_payload(self, parser):
        # Just company ID bytes, no payload
        raw = make_raw(manufacturer_data=bytes.fromhex("6500"))
        assert parser.parse(raw) is None


class TestBosePluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Bose"
