"""Tests for Samsung TV BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.samsung_tv import SamsungTVParser, SAMSUNG_COMPANY_ID, KNOWN_TV_TYPES


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
        name="samsung_tv",
        company_id=SAMSUNG_COMPANY_ID,
        description="Samsung TV and soundbar advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(SamsungTVParser):
        pass

    return registry


def _samsung_mfr_data(type_bytes=b"\x42\x04", payload=b"\x00\x00"):
    """Build manufacturer data: company_id (LE) + type_bytes + payload."""
    return SAMSUNG_COMPANY_ID.to_bytes(2, "little") + type_bytes + payload


class TestSamsungTVParser:
    def test_matches_company_id(self):
        """Matches on Samsung company_id 0x0075."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[TV] Samsung Crystal UHD",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_parse_tv_name(self):
        """Parses TV names with [TV] prefix."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[TV] Samsung Crystal UHD",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.parser_name == "samsung_tv"
        assert result.metadata["model"] == "Samsung Crystal UHD"
        assert result.device_class == "tv"

    def test_parse_soundbar_name(self):
        """Parses soundbar names with [AV] prefix."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[AV] HW-Q990D",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model"] == "HW-Q990D"
        assert result.device_class == "soundbar"

    def test_device_class_tv_from_prefix(self):
        """device_class is 'tv' when local_name starts with [TV]."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[TV] Some Model",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "tv"

    def test_device_class_soundbar_from_prefix(self):
        """device_class is 'soundbar' when local_name starts with [AV]."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[AV] HW-S60D",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "soundbar"

    def test_device_class_tv_from_crystal_uhd_in_name(self):
        """device_class is 'tv' when name contains 'Crystal UHD' without prefix."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="Samsung Crystal UHD 55",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "tv"

    def test_identity_hash_format(self):
        """Identity hash is SHA256('samsung_tv:{mac}')[:16]."""
        registry = _make_registry()
        mac = "11:22:33:44:55:66"
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[TV] Test TV",
            mac_address=mac,
        )
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256(f"samsung_tv:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_for_non_samsung_company_id(self):
        """Returns None when company_id is not Samsung."""
        parser = SamsungTVParser()
        # Apple company_id 0x004C
        data = (0x004C).to_bytes(2, "little") + b"\x42\x04\x00\x00"
        ad = _make_ad(manufacturer_data=data, local_name="[TV] Fake")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_short_manufacturer_data(self):
        """Returns None when manufacturer_data is too short (< 4 bytes)."""
        parser = SamsungTVParser()
        ad = _make_ad(manufacturer_data=b"\x75\x00")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = SamsungTVParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_type_bytes_in_metadata(self):
        """type_bytes extracted from offset 2-3 are in metadata."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(type_bytes=b"\x42\x04"),
            local_name="[TV] Test",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["type_bytes"] == "4204"

    def test_known_tv_type_without_tv_name(self):
        """Known TV type_bytes match even without [TV]/[AV] name prefix."""
        parser = SamsungTVParser()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(type_bytes=b"\x42\x04"),
            local_name="Unknown Device",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.device_class == "tv"

    def test_unknown_type_without_tv_name_returns_none(self):
        """Unknown type_bytes without [TV]/[AV]/Crystal UHD name returns None."""
        parser = SamsungTVParser()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(type_bytes=b"\xFF\xFF"),
            local_name="Some Random Device",
        )
        result = parser.parse(ad)
        assert result is None

    def test_no_model_in_metadata_without_prefix(self):
        """Model is not in metadata when name lacks [TV]/[AV] prefix."""
        parser = SamsungTVParser()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(type_bytes=b"\x42\x04"),
        )
        result = parser.parse(ad)
        assert result is not None
        assert "model" not in result.metadata

    def test_beacon_type(self):
        """beacon_type is 'samsung_tv'."""
        parser = SamsungTVParser()
        ad = _make_ad(
            manufacturer_data=_samsung_mfr_data(),
            local_name="[TV] Test",
        )
        result = parser.parse(ad)
        assert result.beacon_type == "samsung_tv"

    def test_raw_payload_hex(self):
        """raw_payload_hex contains full manufacturer data as hex."""
        parser = SamsungTVParser()
        mfr = _samsung_mfr_data(type_bytes=b"\x42\x04", payload=b"\xAB\xCD")
        ad = _make_ad(manufacturer_data=mfr, local_name="[TV] Test")
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr.hex()
