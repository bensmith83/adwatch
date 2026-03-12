"""Tests for GE Appliances plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.ge_appliances import GEAppliancesParser


GE_COMPANY_ID = 0x0929

# Short ad: company_id + status bytes + zero padding
SHORT_AD = bytes.fromhex("2909b200000000000000000000")

# Long ad: company_id + status bytes + model string (null-terminated) + padding
LONG_AD = bytes.fromhex("2909b10350584432324259504346530000000000000000000000")

GE_MAC = "FC:B9:7E:2B:D1:9E"


@pytest.fixture
def parser():
    return GEAppliancesParser()


def make_raw(manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=GE_MAC,
        address_type="public",
        local_name=None,
        service_data=None,
        service_uuids=[],
        rssi=-65,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        **defaults,
    )


class TestGEAppliancesMatching:
    def test_returns_none_without_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_for_short_data(self, parser):
        raw = make_raw(manufacturer_data=bytes([0x29, 0x09]))
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_company_id(self, parser):
        # Different company ID but same structure
        wrong = bytearray(SHORT_AD)
        wrong[0] = 0xFF
        wrong[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(wrong))
        assert parser.parse(raw) is None


class TestGEAppliancesShortAd:
    def test_parse_short_ad_returns_result(self, parser):
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result.parser_name == "ge_appliances"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result.beacon_type == "ge_appliances"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result.device_class == "smart_home"

    def test_no_model_in_short_ad(self, parser):
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result.metadata.get("model") is None

    def test_ad_variant_byte(self, parser):
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result.metadata["ad_variant"] == 0xB2


class TestGEAppliancesLongAd:
    def test_parse_long_ad_returns_result(self, parser):
        raw = make_raw(manufacturer_data=LONG_AD)
        result = parser.parse(raw)
        assert result is not None

    def test_model_extracted(self, parser):
        raw = make_raw(manufacturer_data=LONG_AD)
        result = parser.parse(raw)
        assert result.metadata["model"] == "PXD22BYPCFS"

    def test_ad_variant_byte(self, parser):
        raw = make_raw(manufacturer_data=LONG_AD)
        result = parser.parse(raw)
        assert result.metadata["ad_variant"] == 0xB1

    def test_status_byte(self, parser):
        raw = make_raw(manufacturer_data=LONG_AD)
        result = parser.parse(raw)
        assert result.metadata["status_byte"] == 0x03


class TestGEAppliancesIdentity:
    def test_stable_identity_across_ad_variants(self, parser):
        """Both ad variants from same MAC should produce same identity hash."""
        short = parser.parse(make_raw(manufacturer_data=SHORT_AD))
        long = parser.parse(make_raw(manufacturer_data=LONG_AD))
        assert short.identifier_hash == long.identifier_hash

    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=SHORT_AD))
        r2 = parser.parse(make_raw(
            manufacturer_data=SHORT_AD,
            mac_address="FC:B9:7E:AA:BB:CC",
        ))
        assert r1.identifier_hash != r2.identifier_hash

    def test_hash_format(self, parser):
        result = parser.parse(make_raw(manufacturer_data=SHORT_AD))
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)


class TestGEAppliancesSubtypeNames:
    def test_short_ad_subtype_name_idle(self, parser):
        """Short ad (variant 0xB2) should have ad_subtype_name='idle'."""
        raw = make_raw(manufacturer_data=SHORT_AD)
        result = parser.parse(raw)
        assert result.metadata["ad_subtype_name"] == "idle"

    def test_long_ad_subtype_name_device_info(self, parser):
        """Long ad (variant 0xB1) should have ad_subtype_name='device_info'."""
        raw = make_raw(manufacturer_data=LONG_AD)
        result = parser.parse(raw)
        assert result.metadata["ad_subtype_name"] == "device_info"

    def test_other_variant_subtype_name_status(self, parser):
        """Other variant byte should have ad_subtype_name='status'."""
        other = bytearray(SHORT_AD)
        other[2] = 0xA0  # different variant byte
        raw = make_raw(manufacturer_data=bytes(other))
        result = parser.parse(raw)
        assert result.metadata["ad_subtype_name"] == "status"


class TestGEAppliancesStableKey:
    def test_stable_key_uses_mac(self, parser):
        """Stable key should be MAC-based so short/long ads dedup together."""
        short = parser.parse(make_raw(manufacturer_data=SHORT_AD))
        long = parser.parse(make_raw(manufacturer_data=LONG_AD))
        assert short.stable_key == long.stable_key
        assert GE_MAC in short.stable_key
