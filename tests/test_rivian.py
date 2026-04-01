"""Tests for Rivian BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.rivian import RivianParser, RIVIAN_COMPANY_ID, MODE_MAP, DEVICE_CLASS_MAP


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
        name="rivian",
        company_id=RIVIAN_COMPANY_ID,
        local_name_pattern=r"^Rivian|^RIVN",
        description="Rivian vehicle and phone key advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(RivianParser):
        pass

    return registry


def _rivian_mfr_data(mode_byte=None, payload=b""):
    """Build manufacturer data: company_id (LE) + optional mode byte + payload."""
    data = RIVIAN_COMPANY_ID.to_bytes(2, "little")
    if mode_byte is not None:
        data += bytes([mode_byte]) + payload
    return data


class TestRivianParser:
    def test_matches_company_id(self):
        """Matches on Rivian company_id 0x0941."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01))
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_rivian(self):
        """Matches on local_name starting with 'Rivian'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Rivian R1T")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_rivn(self):
        """Matches on local_name starting with 'RIVN'."""
        registry = _make_registry()
        ad = _make_ad(local_name="RIVN-12345")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_mode_phone_key(self):
        """Mode byte 0x01 maps to 'phone_key'."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["mode"] == "phone_key"

    def test_mode_vehicle(self):
        """Mode byte 0x17 maps to 'vehicle'."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x17))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["mode"] == "vehicle"

    def test_mode_passive_for_unknown_byte(self):
        """Unknown mode byte defaults to 'passive'."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0xFF))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["mode"] == "passive"

    def test_device_class_phone_key(self):
        """device_class is 'vehicle_key' for phone_key mode."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01))
        result = parser.parse(ad)
        assert result.device_class == "vehicle_key"

    def test_device_class_vehicle_mode(self):
        """device_class is 'vehicle' for vehicle mode."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x17))
        result = parser.parse(ad)
        assert result.device_class == "vehicle"

    def test_device_class_passive_mode(self):
        """device_class is 'vehicle' for passive mode."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0xFF))
        result = parser.parse(ad)
        assert result.device_class == "vehicle"

    def test_identity_hash_format(self):
        """Identity hash is SHA256('rivian:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = RivianParser()
        ad = _make_ad(
            manufacturer_data=_rivian_mfr_data(mode_byte=0x01),
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"rivian:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_no_mfr_no_name(self):
        """Returns None when neither manufacturer data nor name match."""
        parser = RivianParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_wrong_company_id_no_name(self):
        """Returns None when company_id doesn't match and no name."""
        parser = RivianParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x00"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_name_only_match_no_mfr_data(self):
        """Parses successfully with name match and no manufacturer data."""
        parser = RivianParser()
        ad = _make_ad(local_name="Rivian R1S")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "rivian"
        assert result.metadata["mode"] == "passive"
        assert result.metadata["device_name"] == "Rivian R1S"

    def test_name_only_match_wrong_company_id(self):
        """Parses successfully with name match even if company_id is wrong."""
        parser = RivianParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x00"
        ad = _make_ad(manufacturer_data=data, local_name="RIVN-Key")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["mode"] == "passive"
        assert result.metadata["device_name"] == "RIVN-Key"

    def test_mfr_data_exactly_2_bytes(self):
        """With exactly 2 bytes (company_id only), mode defaults to passive."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data())
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["mode"] == "passive"

    def test_short_mfr_data_1_byte(self):
        """1-byte manufacturer data is too short; returns None without name."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=b"\x41")
        result = parser.parse(ad)
        assert result is None

    def test_beacon_type(self):
        """beacon_type is 'rivian'."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01))
        result = parser.parse(ad)
        assert result.beacon_type == "rivian"

    def test_parser_name(self):
        """parser_name is 'rivian'."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01))
        result = parser.parse(ad)
        assert result.parser_name == "rivian"

    def test_raw_payload_hex_with_payload(self):
        """raw_payload_hex contains bytes after company_id."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01, payload=b"\xAB\xCD"))
        result = parser.parse(ad)
        assert result.raw_payload_hex == "01abcd"

    def test_raw_payload_hex_exactly_2_bytes(self):
        """raw_payload_hex is empty when only company_id present."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data())
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_device_name_in_metadata_when_present(self):
        """device_name appears in metadata when local_name is set."""
        parser = RivianParser()
        ad = _make_ad(
            manufacturer_data=_rivian_mfr_data(mode_byte=0x17),
            local_name="Rivian R1T",
        )
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Rivian R1T"

    def test_no_device_name_in_metadata_when_absent(self):
        """device_name not in metadata when local_name is None."""
        parser = RivianParser()
        ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=0x01))
        result = parser.parse(ad)
        assert "device_name" not in result.metadata

    def test_non_matching_name_no_mfr(self):
        """Returns None when name doesn't match pattern and no mfr data."""
        parser = RivianParser()
        ad = _make_ad(local_name="Tesla Model 3")
        result = parser.parse(ad)
        assert result is None

    def test_name_must_start_with_pattern(self):
        """Name containing 'Rivian' but not at start doesn't match."""
        parser = RivianParser()
        ad = _make_ad(local_name="My Rivian Truck")
        result = parser.parse(ad)
        assert result is None

    def test_all_mode_map_entries(self):
        """All entries in MODE_MAP produce correct mode and device_class."""
        parser = RivianParser()
        for mode_byte, mode_name in MODE_MAP.items():
            ad = _make_ad(manufacturer_data=_rivian_mfr_data(mode_byte=mode_byte))
            result = parser.parse(ad)
            assert result.metadata["mode"] == mode_name
            assert result.device_class == DEVICE_CLASS_MAP[mode_name]
