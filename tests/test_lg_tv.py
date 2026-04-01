"""Tests for LG TV BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.lg_tv import LGTVParser, LG_COMPANY_ID


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
        name="lg_tv",
        company_id=LG_COMPANY_ID,
        service_uuid="feb9",
        description="LG webOS TV advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(LGTVParser):
        pass

    return registry


def _lg_mfr_data(flags=0x01, payload=b""):
    """Build manufacturer data: company_id (LE) + flags byte + payload."""
    return LG_COMPANY_ID.to_bytes(2, "little") + bytes([flags]) + payload


class TestLGTVParser:
    def test_matches_company_id(self):
        """Matches on LG company_id 0x00C4."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(),
            local_name="[LG] webOS TV OLED65C3",
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_service_uuid(self):
        """Matches on service UUID feb9."""
        registry = _make_registry()
        ad = _make_ad(
            service_data={"feb9": b"\x01\x02"},
            local_name="[LG] webOS TV OLED65C3",
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_parse_basic(self):
        """Parses valid LG TV advertisement."""
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(flags=0x03),
            local_name="[LG] webOS TV OLED65C3",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "lg_tv"
        assert result.beacon_type == "lg_tv"
        assert result.device_class == "tv"

    def test_parse_model_from_local_name(self):
        """Extracts model from '[LG] webOS TV ' prefix."""
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(),
            local_name="[LG] webOS TV OLED65C3",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model"] == "OLED65C3"

    def test_no_model_without_prefix(self):
        """Model not in metadata when local_name lacks expected prefix."""
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(),
            local_name="Some LG Device",
        )
        result = parser.parse(ad)
        assert result is not None
        assert "model" not in result.metadata

    def test_no_model_when_no_local_name(self):
        """Model not in metadata when local_name is None."""
        parser = LGTVParser()
        ad = _make_ad(manufacturer_data=_lg_mfr_data())
        result = parser.parse(ad)
        assert result is not None
        assert "model" not in result.metadata

    def test_flags_in_metadata(self):
        """Flags byte extracted from offset 2 is in metadata."""
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(flags=0xAB),
            local_name="[LG] webOS TV Test",
        )
        result = parser.parse(ad)
        assert result.metadata["flags"] == 0xAB

    def test_identity_hash_format(self):
        """Identity hash is SHA256('lg_tv:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(),
            local_name="[LG] webOS TV Test",
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"lg_tv:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex contains full manufacturer data as hex."""
        parser = LGTVParser()
        mfr = _lg_mfr_data(flags=0x01, payload=b"\xDE\xAD")
        ad = _make_ad(manufacturer_data=mfr, local_name="[LG] webOS TV Test")
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr.hex()

    def test_returns_none_for_non_lg_company_id(self):
        """Returns None when company_id is not LG."""
        parser = LGTVParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01"
        ad = _make_ad(manufacturer_data=data, local_name="[LG] webOS TV Fake")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_short_manufacturer_data(self):
        """Returns None when manufacturer_data is too short (< 3 bytes)."""
        parser = LGTVParser()
        ad = _make_ad(manufacturer_data=b"\xC4\x00")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = LGTVParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_empty_manufacturer_data(self):
        """Returns None when manufacturer_data is empty bytes."""
        parser = LGTVParser()
        ad = _make_ad(manufacturer_data=b"")
        result = parser.parse(ad)
        assert result is None

    def test_device_class_is_tv(self):
        """device_class is always 'tv'."""
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=_lg_mfr_data(),
            local_name="Unknown",
        )
        result = parser.parse(ad)
        assert result.device_class == "tv"

    def test_minimum_valid_data(self):
        """Exactly 3 bytes (company_id + flags) is valid."""
        parser = LGTVParser()
        ad = _make_ad(
            manufacturer_data=LG_COMPANY_ID.to_bytes(2, "little") + b"\x00",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["flags"] == 0x00

    def test_company_id_constant(self):
        """LG_COMPANY_ID is 0x00C4 (196)."""
        assert LG_COMPANY_ID == 0x00C4
