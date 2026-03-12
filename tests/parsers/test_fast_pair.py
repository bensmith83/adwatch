"""Tests for Google Fast Pair parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.fast_pair import FastPairParser


@pytest.fixture
def parser():
    return FastPairParser()


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


# Discoverable mode: Model ID 0xABCDEF
DISCOVERABLE_DATA = bytes([0xAB, 0xCD, 0xEF])

# Not Discoverable mode: flags=0x02, 2-byte filter, 1-byte salt
NOT_DISCOVERABLE_DATA = bytes([0x02, 0xA1, 0xB2, 0xC3])


class TestFastPairDiscoverable:
    def test_parse_valid_discoverable(self, parser):
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.parser_name == "fast_pair"

    def test_device_class_accessory(self, parser):
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.device_class == "accessory"

    def test_extracts_model_id(self, parser):
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["model_id"] == "abcdef"

    def test_identifier_hash_format(self, parser):
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_and_model_id(self, parser):
        """Discoverable: Identity = SHA256(mac:model_id_hex)[:16]."""
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)

        expected = hashlib.sha256(
            "AA:BB:CC:DD:EE:FF:abcdef".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)


class TestFastPairNotDiscoverable:
    def test_parse_not_discoverable(self, parser):
        raw = make_raw(
            service_data={"fe2c": NOT_DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_extracts_account_key_filter(self, parser):
        raw = make_raw(
            service_data={"fe2c": NOT_DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        # Should have some indication of not-discoverable / account key filter
        assert "account_key_filter" in result.metadata or "filter" in result.metadata


class TestFastPairModelNameLookup:
    def test_known_model_id_has_model_name(self, parser):
        """Discoverable mode with known model ID includes model_name."""
        data = bytes([0xAA, 0xBB, 0x11])  # "aabb11" -> Pixel Buds Pro
        raw = make_raw(
            service_data={"fe2c": data},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["model_name"] == "Pixel Buds Pro"

    def test_unknown_model_id_has_unknown_name(self, parser):
        """Discoverable mode with unknown model ID sets model_name to Unknown."""
        raw = make_raw(
            service_data={"fe2c": DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["model_name"] == "Unknown"

    def test_sony_model_lookup(self, parser):
        data = bytes([0x06, 0x00, 0xD4])  # "0600d4" -> Sony WH-1000XM5
        raw = make_raw(
            service_data={"fe2c": data},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["model_name"] == "Sony WH-1000XM5"


class TestFastPairBatteryNotification:
    def test_battery_parsed_show_notification(self, parser):
        """Not-discoverable with battery extension (type 0x03 = show UI)."""
        # flags=0x02 (filter_len=2), 2 filter bytes, 1 salt byte,
        # then battery: type=0x33 (upper nibble 0x03, lower ignored),
        # left=50%, right=75%, case=0x7F (unknown)
        data = bytes([0x02, 0xA1, 0xB2, 0xC3, 0x33, 50, 75, 0x7F])
        raw = make_raw(
            service_data={"fe2c": data},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["battery_left"] == 50
        assert result.metadata["battery_right"] == 75
        assert result.metadata["battery_case"] is None
        assert result.metadata["charging_left"] is False
        assert result.metadata["charging_right"] is False
        assert result.metadata["charging_case"] is False
        assert result.metadata["battery_show_ui"] is True

    def test_battery_parsed_hide_notification(self, parser):
        """Not-discoverable with battery extension (type 0x04 = hide UI)."""
        data = bytes([0x02, 0xA1, 0xB2, 0xC3, 0x40, 30, 40, 60])
        raw = make_raw(
            service_data={"fe2c": data},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["battery_left"] == 30
        assert result.metadata["battery_right"] == 40
        assert result.metadata["battery_case"] == 60
        assert result.metadata["battery_show_ui"] is False

    def test_battery_charging_flags(self, parser):
        """Bit 7 set means charging."""
        # 0x80 | 90 = 0xDA (charging, 90%)
        # 0x80 | 20 = 0x94 (charging, 20%)
        # 100 = not charging, 100%
        data = bytes([0x02, 0xA1, 0xB2, 0xC3, 0x33, 0x80 | 90, 0x80 | 20, 100])
        raw = make_raw(
            service_data={"fe2c": data},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert result.metadata["battery_left"] == 90
        assert result.metadata["charging_left"] is True
        assert result.metadata["battery_right"] == 20
        assert result.metadata["charging_right"] is True
        assert result.metadata["battery_case"] == 100
        assert result.metadata["charging_case"] is False

    def test_no_battery_when_no_extra_bytes(self, parser):
        """Standard not-discoverable without battery extension has no battery keys."""
        raw = make_raw(
            service_data={"fe2c": NOT_DISCOVERABLE_DATA},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert "battery_left" not in result.metadata

    def test_no_battery_when_invalid_type_nibble(self, parser):
        """Extra bytes with wrong type nibble are not parsed as battery."""
        # type nibble 0x05 is not 0x03 or 0x04
        data = bytes([0x02, 0xA1, 0xB2, 0xC3, 0x50, 50, 50, 50])
        raw = make_raw(
            service_data={"fe2c": data},
            service_uuids=["fe2c"],
        )
        result = parser.parse(raw)

        assert "battery_left" not in result.metadata


class TestFastPairMalformed:
    def test_returns_none_for_no_service_data(self, parser):
        raw = make_raw(service_data=None, service_uuids=[])
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_uuid(self, parser):
        raw = make_raw(
            service_data={"abcd": DISCOVERABLE_DATA},
            service_uuids=["abcd"],
        )
        assert parser.parse(raw) is None

    def test_returns_none_for_empty_data(self, parser):
        raw = make_raw(
            service_data={"fe2c": b""},
            service_uuids=["fe2c"],
        )
        assert parser.parse(raw) is None
