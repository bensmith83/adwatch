"""Tests for Google Nearby Presence plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.google_nearby_presence import GoogleNearbyPresenceParser


@pytest.fixture
def parser():
    return GoogleNearbyPresenceParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-09T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


FCF1_UUID = "fcf1"
# Realistic service data: version byte 0x04 + 20 bytes encrypted payload
SAMPLE_DATA = bytes.fromhex("04444b8e615822e1788bb147382c7fbb102427954658")


class TestGoogleNearbyPresenceParsing:
    def test_parse_with_service_data(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "google_nearby_presence"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "google_nearby_presence"

    def test_device_class_phone(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result.device_class == "phone"

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac(self, parser):
        raw = make_raw(
            service_data={FCF1_UUID: SAMPLE_DATA},
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == SAMPLE_DATA.hex()

    def test_metadata_version(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result.metadata["version"] == 4

    def test_metadata_payload_length(self, parser):
        raw = make_raw(service_data={FCF1_UUID: SAMPLE_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == len(SAMPLE_DATA)

    def test_no_match_empty(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result is None

    def test_no_match_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": SAMPLE_DATA})
        result = parser.parse(raw)
        assert result is None

    def test_empty_service_data(self, parser):
        raw = make_raw(service_data={FCF1_UUID: b""})
        result = parser.parse(raw)
        assert result is None

    def test_match_via_service_uuid_list(self, parser):
        """Match when FCF1 is in service_uuids but service_data has data."""
        raw = make_raw(
            service_data={FCF1_UUID: SAMPLE_DATA},
            service_uuids=[FCF1_UUID],
        )
        result = parser.parse(raw)
        assert result is not None
