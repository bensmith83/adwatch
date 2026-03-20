"""Tests for Jieli Audio chipset plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.jieli_audio import JieliAudioParser


JIELI_COMPANY_ID = 0x05D6

# Real sample from CSV: JLab GO Pop+-App
JLAB_DATA = bytes.fromhex("d60502000600223e5e525220a6021450000b010200000000000000007f")

MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def parser():
    return JieliAudioParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=MAC,
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


class TestJieliAudioParsing:
    def test_parse_valid_returns_result(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert result.parser_name == "jieli_audio"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert result.beacon_type == "jieli_audio"

    def test_device_class_audio(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert result.device_class == "audio"

    def test_version_byte(self, parser):
        """Version byte at offset 2 should be parsed."""
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert result.metadata["version"] == 0x02

    def test_identity_hash(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        expected = hashlib.sha256(f"jieli_audio:{MAC}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "JLab GO Pop+-App"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        # Payload should be hex of manufacturer data after company ID
        assert result.raw_payload_hex == JLAB_DATA[2:].hex()


class TestJieliAudioBrandExtraction:
    def test_brand_from_jlab_name(self, parser):
        raw = make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App")
        result = parser.parse(raw)
        assert "brand" in result.metadata

    def test_no_name_no_brand(self, parser):
        """Without local_name, brand should not be in metadata."""
        raw = make_raw(manufacturer_data=JLAB_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert "brand" not in result.metadata or result.metadata.get("brand") is None


class TestJieliAudioRejection:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        wrong = bytearray(JLAB_DATA)
        wrong[0] = 0xFF
        wrong[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(wrong))
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=bytes([0xD6, 0x05]))
        assert parser.parse(raw) is None


class TestJieliAudioIdentity:
    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=JLAB_DATA, local_name="JLab GO Pop+-App"))
        r2 = parser.parse(make_raw(
            manufacturer_data=JLAB_DATA,
            local_name="JLab GO Pop+-App",
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash
