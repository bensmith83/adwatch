"""Tests for Samsung TV BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.samsung_tv import SamsungTVParser


SAMSUNG_COMPANY_ID = 0x0075

# Real sample data from CSV captures
NAMED_TV_DATA = bytes.fromhex("750042040101ae14bb6eb39bd616bb6eb39bd501000000000000")
NAMED_TV_NAME = "[TV] UN75JU641D"

NAMED_Q6_DATA = bytes.fromhex("75004204012067210f0022014b01010001000000000000000004")
NAMED_Q6_NAME = "[TV] Samsung Q6DAA 75 TV"

UNNAMED_TV_DATA = bytes.fromhex("75004204018060d003dfbb3ff5d203dfbb3ff401000000000000")

ALT_TYPE_DATA = bytes.fromhex("7500021844a113aee3055c03e6882b2275f2768c47852740477d")

SAMSUNG_MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def parser():
    return SamsungTVParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=SAMSUNG_MAC,
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


class TestSamsungTVParsing:
    def test_parse_named_tv_returns_result(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result.parser_name == "samsung_tv"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result.beacon_type == "samsung_tv"

    def test_device_class_tv(self, parser):
        """[TV] prefix -> device_class 'tv'."""
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result.device_class == "tv"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result.raw_payload_hex == NAMED_TV_DATA.hex()


class TestSamsungTVModelExtraction:
    def test_model_from_tv_prefix(self, parser):
        """[TV] UN75JU641D -> model 'UN75JU641D'."""
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result.metadata["model"] == "UN75JU641D"

    def test_model_from_q6(self, parser):
        """[TV] Samsung Q6DAA 75 TV -> model 'Samsung Q6DAA 75 TV'."""
        raw = make_raw(manufacturer_data=NAMED_Q6_DATA, local_name=NAMED_Q6_NAME)
        result = parser.parse(raw)
        assert result.metadata["model"] == "Samsung Q6DAA 75 TV"

    def test_no_model_when_unnamed(self, parser):
        """Unnamed ad should not have model in metadata."""
        raw = make_raw(manufacturer_data=UNNAMED_TV_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert "model" not in result.metadata or result.metadata.get("model") is None


class TestSamsungTVDeviceClassification:
    def test_tv_prefix_is_tv(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name="[TV] SomeModel")
        result = parser.parse(raw)
        assert result.device_class == "tv"

    def test_av_prefix_is_soundbar(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name="[AV] Samsung N850")
        result = parser.parse(raw)
        assert result.device_class == "soundbar"

    def test_crystal_uhd_is_tv(self, parser):
        raw = make_raw(manufacturer_data=UNNAMED_TV_DATA, local_name="75\" Crystal UHD")
        result = parser.parse(raw)
        assert result.device_class == "tv"

    def test_no_name_defaults_to_tv(self, parser):
        """Unnamed Samsung ads default to device_class 'tv'."""
        raw = make_raw(manufacturer_data=UNNAMED_TV_DATA)
        result = parser.parse(raw)
        assert result.device_class == "tv"


class TestSamsungTVTypeBytes:
    def test_type_bytes_4204(self, parser):
        raw = make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME)
        result = parser.parse(raw)
        assert result.metadata["type_bytes"] == "4204"

    def test_type_bytes_0218(self, parser):
        raw = make_raw(manufacturer_data=ALT_TYPE_DATA, local_name="[TV] TestModel")
        result = parser.parse(raw)
        assert result.metadata["type_bytes"] == "0218"


class TestSamsungTVRejection:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_short_data(self, parser):
        raw = make_raw(manufacturer_data=bytes([0x75, 0x00]))
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        wrong = bytearray(NAMED_TV_DATA)
        wrong[0] = 0xFF
        wrong[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(wrong))
        assert parser.parse(raw) is None


class TestSamsungTVIdentity:
    def test_same_mac_same_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME))
        r2 = parser.parse(make_raw(manufacturer_data=UNNAMED_TV_DATA))
        assert r1.identifier_hash == r2.identifier_hash

    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=NAMED_TV_DATA, local_name=NAMED_TV_NAME))
        r2 = parser.parse(make_raw(
            manufacturer_data=NAMED_TV_DATA,
            local_name=NAMED_TV_NAME,
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash


# Samsung phone manufacturer data — company 0x0075 but NOT a TV type
SAMSUNG_PHONE_DATA = bytes.fromhex("7500011044a113aee3055c03e6882b2275f2768c47852740477d")


class TestSamsungTVFalsePositiveFiltering:
    def test_rejects_unknown_type_no_name(self, parser):
        """Samsung ads with unknown type_bytes and no TV name should be rejected."""
        raw = make_raw(manufacturer_data=SAMSUNG_PHONE_DATA)
        assert parser.parse(raw) is None

    def test_accepts_known_type_4204_no_name(self, parser):
        """Unnamed ads with known TV type '4204' should still parse."""
        raw = make_raw(manufacturer_data=UNNAMED_TV_DATA)
        result = parser.parse(raw)
        assert result is not None

    def test_rejects_non_tv_name(self, parser):
        """Samsung ads with non-TV names should be rejected."""
        raw = make_raw(manufacturer_data=SAMSUNG_PHONE_DATA, local_name="Galaxy S24")
        assert parser.parse(raw) is None

    def test_accepts_tv_name_with_any_type(self, parser):
        """[TV] prefixed names should always be accepted regardless of type_bytes."""
        raw = make_raw(manufacturer_data=SAMSUNG_PHONE_DATA, local_name="[TV] SomeModel")
        result = parser.parse(raw)
        assert result is not None

    def test_accepts_av_name_with_any_type(self, parser):
        """[AV] prefixed names should always be accepted."""
        raw = make_raw(manufacturer_data=SAMSUNG_PHONE_DATA, local_name="[AV] Soundbar")
        result = parser.parse(raw)
        assert result is not None

    def test_accepts_crystal_uhd_name_with_any_type(self, parser):
        """Crystal UHD names should always be accepted."""
        raw = make_raw(manufacturer_data=SAMSUNG_PHONE_DATA, local_name='75" Crystal UHD')
        result = parser.parse(raw)
        assert result is not None

    def test_rejects_alt_type_no_name(self, parser):
        """Type 0218 without a TV name should be rejected (could be any Samsung device)."""
        raw = make_raw(manufacturer_data=ALT_TYPE_DATA)
        assert parser.parse(raw) is None
