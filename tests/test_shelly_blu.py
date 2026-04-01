"""Tests for Shelly BLU sensor BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.shelly_blu import ShellyBluParser, SHELLY_COMPANY_ID


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="shelly_blu",
        company_id=SHELLY_COMPANY_ID,
        local_name_pattern=r"^SB[A-Z]{2}-",
        description="Shelly BLU sensor advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ShellyBluParser):
        pass

    return registry


def _shelly_mfr_data(device_type=0x01, packet_counter=0x05, battery=85, extra=b""):
    """Build manufacturer data: company_id (LE) + device_type + packet_counter + battery + extra."""
    payload = bytes([device_type, packet_counter, battery]) + extra
    return SHELLY_COMPANY_ID.to_bytes(2, "little") + payload


class TestShellyBluParser:
    # --- Registry matching ---

    def test_matches_company_id_0x0BA9(self):
        """Matches on Shelly company_id 0x0BA9."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name 'SBBT-002C' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBBT-002C",
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    # --- Basic fields ---

    def test_parser_name(self):
        """parser_name is 'shelly_blu'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "shelly_blu"

    def test_beacon_type(self):
        """beacon_type is 'shelly_blu'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "shelly_blu"

    def test_device_class_sensor(self):
        """device_class is 'sensor'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.device_class == "sensor"

    # --- Manufacturer data parsing ---

    def test_device_type_from_payload(self):
        """metadata['device_type'] is byte 0 of payload."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data(device_type=0x03))
        result = parser.parse(ad)
        assert result.metadata["device_type"] == 0x03

    def test_packet_counter_from_payload(self):
        """metadata['packet_counter'] is byte 1 of payload."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data(packet_counter=0xAB))
        result = parser.parse(ad)
        assert result.metadata["packet_counter"] == 0xAB

    def test_battery_level_from_payload(self):
        """metadata['battery_level'] is byte 2 of payload."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data(battery=72))
        result = parser.parse(ad)
        assert result.metadata["battery_level"] == 72

    # --- Device model from local_name ---

    def test_model_blu_button(self):
        """'SBBT-002C' -> model='BLU Button'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBBT-002C",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Button"

    def test_model_blu_door_window(self):
        """'SBDW-002C' -> model='BLU Door/Window'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBDW-002C",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Door/Window"

    def test_model_blu_motion(self):
        """'SBMO-003Z' -> model='BLU Motion'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBMO-003Z",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Motion"

    def test_model_blu_ht(self):
        """'SBHT-003C' -> model='BLU H&T'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBHT-003C",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU H&T"

    def test_model_unknown_prefix(self):
        """'SBXX-001A' -> model='BLU Unknown'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBXX-001A",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Unknown"

    def test_model_no_local_name(self):
        """None local_name -> model='Unknown'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["model"] == "Unknown"

    # --- local_name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to raw local_name value."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBBT-002C",
        )
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "SBBT-002C"

    def test_local_name_none_in_metadata(self):
        """metadata['local_name'] is None when local_name not set."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["local_name"] is None

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:shelly_blu)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:shelly_blu".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex(self):
        """raw_payload_hex contains hex of manufacturer payload (without company_id)."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data(device_type=0xAA, packet_counter=0xBB, battery=0xCC))
        result = parser.parse(ad)
        assert result.raw_payload_hex == bytes([0xAA, 0xBB, 0xCC]).hex()

    # --- Edge cases ---

    def test_returns_none_wrong_company_id(self):
        """Returns None when company_id is not Shelly."""
        parser = ShellyBluParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = ShellyBluParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_data(self):
        """Returns None when payload < 3 bytes (company_id + 2 bytes only)."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=SHELLY_COMPANY_ID.to_bytes(2, "little") + b"\x01\x02")
        result = parser.parse(ad)
        assert result is None

    def test_handles_extra_payload_bytes(self):
        """Handles extra payload bytes beyond the 3 required without crashing."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data(extra=b"\xDE\xAD\xBE\xEF"))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["battery_level"] == 85
        assert result.parser_name == "shelly_blu"
