"""Tests for Jieli Audio chipset BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.jieli_audio import JieliAudioParser, JIELI_COMPANY_ID


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
        name="jieli_audio",
        company_id=JIELI_COMPANY_ID,
        description="Jieli Audio chipset advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(JieliAudioParser):
        pass

    return registry


def _jieli_mfr_data(version=0x01, payload=b"\x00\x00"):
    """Build manufacturer data: company_id (LE) + version byte + payload."""
    return JIELI_COMPANY_ID.to_bytes(2, "little") + bytes([version]) + payload


class TestJieliAudioParser:
    def test_company_id_value(self):
        """JIELI_COMPANY_ID is 0x05D6."""
        assert JIELI_COMPANY_ID == 0x05D6

    def test_matches_company_id(self):
        """Matches on Jieli company_id 0x05D6."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_jieli_mfr_data())
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_parse_basic(self):
        """Parses basic Jieli advertisement."""
        parser = JieliAudioParser()
        ad = _make_ad(manufacturer_data=_jieli_mfr_data(version=0x02))
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "jieli_audio"
        assert result.beacon_type == "jieli_audio"
        assert result.device_class == "audio"

    def test_version_in_metadata(self):
        """Version byte extracted from offset 2 is in metadata."""
        parser = JieliAudioParser()
        ad = _make_ad(manufacturer_data=_jieli_mfr_data(version=0x03))
        result = parser.parse(ad)
        assert result.metadata["version"] == 0x03

    def test_device_name_from_local_name(self):
        """device_name in metadata comes from local_name."""
        parser = JieliAudioParser()
        ad = _make_ad(
            manufacturer_data=_jieli_mfr_data(),
            local_name="JBL Flip 6",
        )
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "JBL Flip 6"

    def test_brand_extracted_from_local_name(self):
        """Brand is first word of local_name."""
        parser = JieliAudioParser()
        ad = _make_ad(
            manufacturer_data=_jieli_mfr_data(),
            local_name="Edifier W820NB",
        )
        result = parser.parse(ad)
        assert result.metadata["brand"] == "Edifier"

    def test_brand_single_word_name(self):
        """Brand works with single-word local_name."""
        parser = JieliAudioParser()
        ad = _make_ad(
            manufacturer_data=_jieli_mfr_data(),
            local_name="Speaker",
        )
        result = parser.parse(ad)
        assert result.metadata["brand"] == "Speaker"
        assert result.metadata["device_name"] == "Speaker"

    def test_no_device_name_without_local_name(self):
        """No device_name or brand in metadata when local_name is absent."""
        parser = JieliAudioParser()
        ad = _make_ad(manufacturer_data=_jieli_mfr_data())
        result = parser.parse(ad)
        assert "device_name" not in result.metadata
        assert "brand" not in result.metadata

    def test_identity_hash_format(self):
        """Identity hash is SHA256('jieli_audio:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = JieliAudioParser()
        ad = _make_ad(
            manufacturer_data=_jieli_mfr_data(),
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"jieli_audio:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_differs_by_mac(self):
        """Different MACs produce different identity hashes."""
        parser = JieliAudioParser()
        ad1 = _make_ad(manufacturer_data=_jieli_mfr_data(), mac_address="AA:BB:CC:DD:EE:01")
        ad2 = _make_ad(manufacturer_data=_jieli_mfr_data(), mac_address="AA:BB:CC:DD:EE:02")
        r1 = parser.parse(ad1)
        r2 = parser.parse(ad2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_raw_payload_hex(self):
        """raw_payload_hex contains payload from offset 2 onward."""
        parser = JieliAudioParser()
        mfr = _jieli_mfr_data(version=0x05, payload=b"\xAB\xCD\xEF")
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        # payload is mfr[2:] which is version byte + extra payload
        assert result.raw_payload_hex == mfr[2:].hex()

    def test_returns_none_for_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = JieliAudioParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_short_manufacturer_data(self):
        """Returns None when manufacturer_data is too short (< 3 bytes)."""
        parser = JieliAudioParser()
        ad = _make_ad(manufacturer_data=b"\xD6\x05")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_wrong_company_id(self):
        """Returns None when company_id is not Jieli."""
        parser = JieliAudioParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x00\x00"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_empty_manufacturer_data(self):
        """Returns None when manufacturer_data is empty bytes."""
        parser = JieliAudioParser()
        ad = _make_ad(manufacturer_data=b"")
        result = parser.parse(ad)
        assert result is None

    def test_minimum_valid_length(self):
        """Parses successfully with exactly 3 bytes (company_id + version)."""
        parser = JieliAudioParser()
        mfr = JIELI_COMPANY_ID.to_bytes(2, "little") + b"\x01"
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["version"] == 0x01

    def test_version_zero(self):
        """Handles version byte of 0x00."""
        parser = JieliAudioParser()
        ad = _make_ad(manufacturer_data=_jieli_mfr_data(version=0x00))
        result = parser.parse(ad)
        assert result.metadata["version"] == 0

    def test_large_payload(self):
        """Handles larger payloads correctly."""
        parser = JieliAudioParser()
        payload = bytes(range(256))
        ad = _make_ad(manufacturer_data=_jieli_mfr_data(version=0x01, payload=payload))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["version"] == 0x01
