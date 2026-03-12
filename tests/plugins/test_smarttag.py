"""Tests for Samsung SmartTag plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.smarttag import SmartTagParser


@pytest.fixture
def parser():
    return SmartTagParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
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
        **defaults,
    )


SMARTTAG_DATA = bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x60])

# 20-byte payload: privacy_id(8) + aging_counter(2) + signature(8) + state(1) + reserved(1)
# State byte 0b10_1_01010 = 0xAA → lost_mode=0b10=lost, uwb=1, battery=0b01010=10
SMARTTAG_20B = (
    bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])  # privacy_id
    + bytes([0x00, 0x3C])  # aging_counter = 60
    + bytes([0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8])  # signature
    + bytes([0xAA])  # state: lost_mode=10, uwb=1, battery=01010=10
    + bytes([0x00])  # reserved
)


class TestSmartTagParsing:
    def test_parse_valid_smarttag(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "smarttag"

    def test_device_class_tracker(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA})
        result = parser.parse(raw)
        assert result.device_class == "tracker"

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac:service_data_hex)[:16]."""
        raw = make_raw(
            service_data={"fd5a": SMARTTAG_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{SMARTTAG_DATA.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == SMARTTAG_DATA.hex()

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "SmartTag"


class TestSmartTag20BytePayload:
    def test_privacy_id(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["privacy_id"] == "0102030405060708"

    def test_aging_counter(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["aging_counter"] == 60

    def test_signature(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["signature"] == "a1a2a3a4a5a6a7a8"

    def test_lost_mode_lost(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["lost_mode"] == "lost"

    def test_uwb_available(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["uwb_available"] is True

    def test_battery_level(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["battery_level"] == 10

    def test_payload_hex_still_present(self, parser):
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B})
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == SMARTTAG_20B.hex()

    def test_identity_uses_privacy_id(self, parser):
        """20-byte payloads should hash using privacy_id, not full payload."""
        raw = make_raw(service_data={"fd5a": SMARTTAG_20B}, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:0102030405060708".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_lost_mode_normal(self, parser):
        """State byte 0b00_0_00000 = 0x00 → normal."""
        data = SMARTTAG_20B[:18] + bytes([0x00, 0x00])
        raw = make_raw(service_data={"fd5a": data})
        result = parser.parse(raw)
        assert result.metadata["lost_mode"] == "normal"

    def test_lost_mode_near_owner(self, parser):
        """State byte 0b01_0_00000 = 0x40 → near_owner."""
        data = SMARTTAG_20B[:18] + bytes([0x40, 0x00])
        raw = make_raw(service_data={"fd5a": data})
        result = parser.parse(raw)
        assert result.metadata["lost_mode"] == "near_owner"

    def test_lost_mode_overmature_lost(self, parser):
        """State byte 0b11_0_00000 = 0xC0 → overmature_lost."""
        data = SMARTTAG_20B[:18] + bytes([0xC0, 0x00])
        raw = make_raw(service_data={"fd5a": data})
        result = parser.parse(raw)
        assert result.metadata["lost_mode"] == "overmature_lost"

    def test_uwb_not_available(self, parser):
        """State byte with UWB bit clear."""
        data = SMARTTAG_20B[:18] + bytes([0x80, 0x00])  # 0b10_0_00000
        raw = make_raw(service_data={"fd5a": data})
        result = parser.parse(raw)
        assert result.metadata["uwb_available"] is False

    def test_battery_max(self, parser):
        """Battery level 31 (0b11111)."""
        data = SMARTTAG_20B[:18] + bytes([0x1F, 0x00])  # 0b00_0_11111
        raw = make_raw(service_data={"fd5a": data})
        result = parser.parse(raw)
        assert result.metadata["battery_level"] == 31


class TestSmartTagBackwardCompat:
    def test_short_payload_still_works(self, parser):
        """Non-20-byte payloads should still return basic result."""
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["payload_hex"] == SMARTTAG_DATA.hex()
        assert "privacy_id" not in result.metadata

    def test_short_payload_identity_hash_unchanged(self, parser):
        """Short payloads use full payload for identity hash (existing behavior)."""
        raw = make_raw(service_data={"fd5a": SMARTTAG_DATA}, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{SMARTTAG_DATA.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestSmartTagMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": SMARTTAG_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(service_data={"fd5a": b""})
        assert parser.parse(raw) is None
