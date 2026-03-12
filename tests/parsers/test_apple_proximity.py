"""Tests for Apple Proximity Pairing parser (AirPods/Beats)."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.apple_proximity import AppleProximityParser


@pytest.fixture
def parser():
    return AppleProximityParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# AirPods Pro 2nd Gen: L=80% R=90% Case=60%, right charging, lid closed
# 4c 00 07 19 01 14 20 24 89 60 02
AIRPODS_PRO2_PAYLOAD = bytes([
    0x4C, 0x00,  # Apple company ID
    0x07,        # Type: Proximity Pairing
    0x19,        # Length: 25
    0x01,        # Prefix byte
    0x14, 0x20,  # Device model: 0x1420 = AirPods Pro 2nd Gen
    0x24,        # UTP byte (charging flags)
    0x89,        # Battery: left=8 (80%), right=9 (90%)
    0x60,        # Battery: case=6 (60%), lid=closed (0x0)
    0x02,        # Color code
])


class TestAppleProximityParser:
    def test_parse_valid_proximity(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "apple_proximity"

    def test_device_class_accessory(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.device_class == "accessory"

    def test_extracts_device_model(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["device_model"] == 0x1420

    def test_extracts_battery_left(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["battery_left"] == 80

    def test_extracts_battery_right(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["battery_right"] == 90

    def test_extracts_battery_case(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["battery_case"] == 60

    def test_extracts_charging_state(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        # UTP byte 0x24: some charging flag is set
        assert "charging" in result.metadata or "utp" in result.metadata

    def test_lid_closed(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        # Low nibble of byte 5 is 0x0 = lid closed
        assert result.metadata.get("lid_open") is False or result.metadata.get("lid_open") == 0

    def test_lid_open(self, parser):
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[9] = 0x61  # case=6, lid=open (low nibble non-zero)
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata.get("lid_open") is True or result.metadata.get("lid_open") == 1

    def test_identifier_hash_format(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_model_payload(self, parser):
        """Identity = SHA256(mac:model_hex:first_7_bytes_hex)[:16]."""
        raw = make_raw(AIRPODS_PRO2_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)

        first_7 = AIRPODS_PRO2_PAYLOAD[4:11]  # TLV value bytes 0-6
        model_hex = "1420"
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{model_hex}:{first_7.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_tlv_type(self, parser):
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[2] = 0x10  # Nearby Info
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        # Less than minimum 7 bytes in TLV value
        raw = make_raw(bytes([0x4C, 0x00, 0x07, 0x03, 0x01, 0x14, 0x20]))
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[0] = 0x06
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_battery_clamped_to_100(self, parser):
        """Values above 10 should be clamped to 100%."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[8] = 0xFF  # left=15, right=15 (both > 10)
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["battery_left"] == 100
        assert result.metadata["battery_right"] == 100

    # --- Model name lookup ---

    def test_model_name_known(self, parser):
        """Known device model should resolve to a friendly name."""
        raw = make_raw(AIRPODS_PRO2_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["model_name"] == "AirPods Pro 2"

    def test_model_name_unknown(self, parser):
        """Unknown device model should produce 'Unknown'."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[5] = 0xFF  # change model to 0xFF20 (unknown)
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["model_name"] == "Unknown"

    def test_model_name_airpods_1st_gen(self, parser):
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[5] = 0x02
        data[6] = 0x20  # 0x0220
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["model_name"] == "AirPods 1st Gen"

    # --- Charging status ---

    def test_charging_left(self, parser):
        """UTP bit 0 = left bud charging."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x01  # UTP: only bit 0 set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["charging_left"] is True
        assert result.metadata["charging_right"] is False
        assert result.metadata["charging_case"] is False

    def test_charging_right(self, parser):
        """UTP bit 1 = right bud charging."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x02  # UTP: only bit 1 set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["charging_left"] is False
        assert result.metadata["charging_right"] is True
        assert result.metadata["charging_case"] is False

    def test_charging_case(self, parser):
        """UTP bit 2 = case charging."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x04  # UTP: only bit 2 set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["charging_left"] is False
        assert result.metadata["charging_right"] is False
        assert result.metadata["charging_case"] is True

    def test_charging_all(self, parser):
        """All three charging bits set."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x07  # UTP: bits 0,1,2 all set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["charging_left"] is True
        assert result.metadata["charging_right"] is True
        assert result.metadata["charging_case"] is True

    # --- In-ear detection ---

    def test_in_ear_left(self, parser):
        """UTP bit 3 = left bud in ear."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x08  # UTP: only bit 3 set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["in_ear_left"] is True
        assert result.metadata["in_ear_right"] is False

    def test_in_ear_right(self, parser):
        """UTP bit 4 = right bud in ear."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x10  # UTP: only bit 4 set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["in_ear_left"] is False
        assert result.metadata["in_ear_right"] is True

    def test_in_ear_both(self, parser):
        """Both in-ear bits set."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x18  # UTP: bits 3 and 4 set
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["in_ear_left"] is True
        assert result.metadata["in_ear_right"] is True

    def test_utp_combined_flags(self, parser):
        """UTP byte with charging + in-ear bits combined."""
        data = bytearray(AIRPODS_PRO2_PAYLOAD)
        data[7] = 0x1D  # bits: 0,2,3,4 = left charging, case charging, both in ear
        raw = make_raw(bytes(data))
        result = parser.parse(raw)

        assert result.metadata["charging_left"] is True
        assert result.metadata["charging_right"] is False
        assert result.metadata["charging_case"] is True
        assert result.metadata["in_ear_left"] is True
        assert result.metadata["in_ear_right"] is True
