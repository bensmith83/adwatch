"""Tests for Google Android Nearby plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.google_android_nearby import GoogleAndroidNearbyParser


@pytest.fixture
def parser():
    return GoogleAndroidNearbyParser()


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
LONG_FRAME = bytes.fromhex("4a17234a54574a1132653328bfc6bac83e76863639467e2e3eb682")
SHORT_FRAME_1101 = bytes.fromhex("1101a13a95ab")
SHORT_FRAME_1102 = bytes.fromhex("1102e41d37c329fa0d09")


class TestAndroidNearbyParsing:
    def test_parse_long_frame(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_short_frame_1101(self, parser):
        raw = make_raw(service_data={"fef3": SHORT_FRAME_1101})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_short_frame_1102(self, parser):
        raw = make_raw(service_data={"fef3": SHORT_FRAME_1102})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.parser_name == "google_android_nearby"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.beacon_type == "google_android_nearby"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.device_class == "phone"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.raw_payload_hex == LONG_FRAME.hex()


class TestAndroidNearbyIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_identity_hash_value(self, parser):
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        expected = hashlib.sha256(b"google_android_nearby:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_frame_types(self, parser):
        """All frame types from same MAC should have same identity."""
        r1 = parser.parse(make_raw(service_data={"fef3": LONG_FRAME}))
        r2 = parser.parse(make_raw(service_data={"fef3": SHORT_FRAME_1101}))
        r3 = parser.parse(make_raw(service_data={"fef3": SHORT_FRAME_1102}))
        assert r1.identifier_hash == r2.identifier_hash == r3.identifier_hash

    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(service_data={"fef3": LONG_FRAME}))
        r2 = parser.parse(make_raw(
            service_data={"fef3": LONG_FRAME},
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash


class TestAndroidNearbyFrameTypes:
    def test_long_frame_type(self, parser):
        """Long frame (4a17 prefix) should report frame_type in metadata."""
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == "long"

    def test_short_frame_type_1101(self, parser):
        """Short frame (1101 prefix) should report frame_type as short."""
        raw = make_raw(service_data={"fef3": SHORT_FRAME_1101})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == "short"

    def test_short_frame_type_1102(self, parser):
        """Extended short frame (1102 prefix) should report frame_type as short_extended."""
        raw = make_raw(service_data={"fef3": SHORT_FRAME_1102})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == "short_extended"

    def test_long_frame_magic_bytes(self, parser):
        """Long frame should report magic bytes 0x4a17."""
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.metadata["magic"] == "4a17"

    def test_short_frame_magic_bytes(self, parser):
        raw = make_raw(service_data={"fef3": SHORT_FRAME_1101})
        result = parser.parse(raw)
        assert result.metadata["magic"] == "1101"

    def test_1102_frame_magic_bytes(self, parser):
        raw = make_raw(service_data={"fef3": SHORT_FRAME_1102})
        result = parser.parse(raw)
        assert result.metadata["magic"] == "1102"

    def test_data_length_in_metadata(self, parser):
        """Should report data length in metadata."""
        raw = make_raw(service_data={"fef3": LONG_FRAME})
        result = parser.parse(raw)
        assert result.metadata["data_length"] == 26


class TestAndroidNearbyRejectsInvalid:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": LONG_FRAME})
        assert parser.parse(raw) is None

    def test_returns_none_too_short_data(self, parser):
        """Service data shorter than 2 bytes should be rejected."""
        raw = make_raw(service_data={"fef3": bytes(1)})
        assert parser.parse(raw) is None

    def test_returns_none_empty_service_data(self, parser):
        raw = make_raw(service_data={})
        assert parser.parse(raw) is None

    def test_returns_none_unrelated_ad(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c000215aabbccdd"))
        assert parser.parse(raw) is None
