"""Tests for Amazon Fire TV plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.amazon_fire_tv import AmazonFireTVParser


@pytest.fixture
def parser():
    return AmazonFireTVParser()


def make_raw(service_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


# Real sample data from CSV
SVC_DATA_20 = bytes.fromhex("00092f06a181b65da3907bc10a4b4b4463000102")
SVC_DATA_22 = bytes.fromhex("00cf3bdbf5a2f2c2b05a1669a6465042730001020001")

FIRE_TV_MAC = "AA:BB:CC:DD:EE:FF"


class TestFireTVParsing:
    def test_parse_20_byte_variant(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_22_byte_variant(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_22}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.parser_name == "amazon_fire_tv"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.beacon_type == "amazon_fire_tv"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.device_class == "streaming_device"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.raw_payload_hex == SVC_DATA_20.hex()


class TestFireTVIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_identity_hash_value(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        expected = hashlib.sha256(b"amazon_fire_tv:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_variants(self, parser):
        """Both 20-byte and 22-byte ads from same MAC should have same identity."""
        r1 = parser.parse(make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV"))
        r2 = parser.parse(make_raw(service_data={"fe00": SVC_DATA_22}, local_name="Fire TV"))
        assert r1.identifier_hash == r2.identifier_hash

    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV"))
        r2 = parser.parse(make_raw(
            service_data={"fe00": SVC_DATA_20},
            local_name="Fire TV",
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash


class TestFireTVDeviceType:
    def test_device_type_kkdc_20_byte(self, parser):
        """20-byte ad has device type bytes KKDc (0x4b4b4463) at offset 10-13."""
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.metadata["device_type_code"] == "KKDc"

    def test_device_type_fpbs_22_byte(self, parser):
        """22-byte ad has device type bytes FPBs (0x46504273) at offset 10-13."""
        raw = make_raw(service_data={"fe00": SVC_DATA_22}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.metadata["device_type_code"] == "FPBs"

    def test_header_byte_always_zero(self, parser):
        """Header byte (offset 0) should be reported in metadata."""
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.metadata["header"] == 0x00


class TestFireTVMatching:
    def test_match_by_service_uuid_only(self, parser):
        """Should parse with just fe00 service data, no local_name."""
        raw = make_raw(service_data={"fe00": SVC_DATA_20})
        result = parser.parse(raw)
        assert result is not None

    def test_match_with_local_name(self, parser):
        """Should parse with both fe00 service data and Fire TV name."""
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result is not None

    def test_metadata_local_name_present(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20}, local_name="Fire TV")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Fire TV"

    def test_metadata_local_name_absent(self, parser):
        raw = make_raw(service_data={"fe00": SVC_DATA_20})
        result = parser.parse(raw)
        assert "device_name" not in result.metadata or result.metadata.get("device_name") is None


class TestFireTVRejectsInvalid:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(local_name="Fire TV")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": SVC_DATA_20})
        assert parser.parse(raw) is None

    def test_returns_none_too_short_data(self, parser):
        """Service data shorter than 14 bytes should be rejected (need offset 10-13)."""
        raw = make_raw(service_data={"fe00": bytes(10)})
        assert parser.parse(raw) is None

    def test_returns_none_empty_service_data(self, parser):
        raw = make_raw(service_data={})
        assert parser.parse(raw) is None

    def test_returns_none_unrelated_ad(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c000215aabbccdd"))
        assert parser.parse(raw) is None
