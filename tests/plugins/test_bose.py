"""Tests for Bose audio device plugin.

Identifier constants per apk-ble-hunting/reports/bose-bosemusic_passive.md.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.bose import BoseParser, BOSE_COMPANY_ID, BOSE_SERVICE_UUID_FEBE


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


# Bose SIG company ID 0x009E (little-endian: 9e 00) + arbitrary payload.
BOSE_MFR_DATA = BOSE_COMPANY_ID.to_bytes(2, "little") + bytes.fromhex("01c901")
BOSE_PAYLOAD = bytes.fromhex("01c901")

FEBE_SERVICE_DATA = bytes(range(36))


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
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
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

    def test_metadata_with_febe_service_data(self, parser):
        raw = make_raw(
            manufacturer_data=BOSE_MFR_DATA,
            service_data={BOSE_SERVICE_UUID_FEBE: FEBE_SERVICE_DATA},
        )
        result = parser.parse(raw)
        assert result.metadata["service_payload_hex"] == FEBE_SERVICE_DATA.hex()
        assert result.metadata["service_payload_length"] == len(FEBE_SERVICE_DATA)


class TestBoseMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        # Apple company ID 0x004C, no other Bose signal → no match.
        raw = make_raw(manufacturer_data=bytes.fromhex("4c0001c901"))
        assert parser.parse(raw) is None

    def test_returns_none_empty_payload_no_other_signal(self, parser):
        # Bose company ID but zero-length payload and no other Bose signal → no match.
        raw = make_raw(manufacturer_data=BOSE_COMPANY_ID.to_bytes(2, "little"))
        assert parser.parse(raw) is None


class TestBosePluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Bose"
