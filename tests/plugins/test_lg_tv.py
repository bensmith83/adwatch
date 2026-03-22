"""Tests for LG TV BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.lg_tv import LGTVParser


LG_COMPANY_ID = 0x00C4
LG_SERVICE_UUID = "feb9"

# Real sample data
NAMED_DATA = bytes.fromhex("c4000234151317fd80")
NAMED_NAME = "[LG] webOS TV UT8000AUA"

UNNAMED_DATA = bytes.fromhex("c4000134151317fd80")

LG_MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def parser():
    return LGTVParser()


def make_raw(manufacturer_data=None, local_name=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=LG_MAC,
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        service_uuids=service_uuids or [],
        **defaults,
    )


class TestLGTVParsing:
    def test_parse_named_returns_result(self, parser):
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result.parser_name == "lg_tv"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result.beacon_type == "lg_tv"

    def test_device_class_tv(self, parser):
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result.device_class == "tv"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result.raw_payload_hex == NAMED_DATA.hex()


class TestLGTVModelExtraction:
    def test_model_from_name(self, parser):
        """[LG] webOS TV UT8000AUA -> model 'UT8000AUA'."""
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result.metadata["model"] == "UT8000AUA"

    def test_no_model_when_unnamed(self, parser):
        raw = make_raw(manufacturer_data=UNNAMED_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert "model" not in result.metadata or result.metadata.get("model") is None


class TestLGTVFlagsByte:
    def test_flags_byte_0x02(self, parser):
        """Named sample has flags byte 0x02 at offset 2."""
        raw = make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME)
        result = parser.parse(raw)
        assert result.metadata["flags"] == 0x02

    def test_flags_byte_0x01(self, parser):
        """Unnamed sample has flags byte 0x01 at offset 2."""
        raw = make_raw(manufacturer_data=UNNAMED_DATA)
        result = parser.parse(raw)
        assert result.metadata["flags"] == 0x01


class TestLGTVRejection:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_short_data(self, parser):
        raw = make_raw(manufacturer_data=bytes([0xC4, 0x00]))
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        wrong = bytearray(NAMED_DATA)
        wrong[0] = 0xFF
        wrong[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(wrong))
        assert parser.parse(raw) is None


class TestLGTVIdentity:
    def test_same_mac_same_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME))
        r2 = parser.parse(make_raw(manufacturer_data=UNNAMED_DATA))
        assert r1.identifier_hash == r2.identifier_hash

    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=NAMED_DATA, local_name=NAMED_NAME))
        r2 = parser.parse(make_raw(
            manufacturer_data=NAMED_DATA,
            local_name=NAMED_NAME,
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash
