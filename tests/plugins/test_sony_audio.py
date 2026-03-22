"""Tests for Sony Audio plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.sony_audio import SonyAudioParser


SONY_COMPANY_ID = 0x012D

# Real samples from CSV
# LE_SRS-XB33 manufacturer data (20 bytes including company ID)
SONY_MFR_DATA = bytes.fromhex("2d0104000101100415afc3d60206c20000000000")

# LE_SRS-XB33 fe2c service data (frame type 0x00, sub-type 0x90)
SONY_FE2C_TYPE00_90 = bytes.fromhex("0090d435499156ec2890ac110e")

# Simple fe2c frame (type 0x00, sub-type 0x00)
SONY_FE2C_TYPE00_SIMPLE = bytes.fromhex("0000342c50ff")

# Type 0x30 frame
SONY_FE2C_TYPE30 = bytes.fromhex("0030000000211782347fe4ca")

# Google FMDN data on fe2c (starts with 0x40 — must NOT be parsed by Sony)
GOOGLE_FMDN_FE2C = bytes.fromhex("40112233445566778899aabb")


@pytest.fixture
def parser():
    return SonyAudioParser()


def make_raw(manufacturer_data=None, service_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


class TestSonyAudioManufacturerData:
    def test_parse_mfr_data_returns_result(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.parser_name == "sony_audio"

    def test_beacon_type(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.beacon_type == "sony_audio"

    def test_device_class_speaker(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.device_class == "speaker"

    def test_identity_hash_format(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.raw_payload_hex == SONY_MFR_DATA.hex()

    def test_model_extracted_from_name(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "SRS-XB33"


class TestSonyAudioFe2cType00:
    def test_parse_fe2c_type00_subtype90(self, parser):
        """Frame type 0x00, sub-type 0x90 (speaker)."""
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE00_90},
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_fe2c_type00_frame_type(self, parser):
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE00_90},
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 0x00

    def test_fe2c_type00_sub_type(self, parser):
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE00_90},
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.metadata["sub_type"] == 0x90

    def test_parse_fe2c_type00_simple(self, parser):
        """Simple frame: type 0x00, sub-type 0x00."""
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE00_SIMPLE},
        )
        result = parser.parse(raw)
        assert result is not None

    def test_fe2c_simple_frame_type(self, parser):
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE00_SIMPLE},
        )
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 0x00
        assert result.metadata["sub_type"] == 0x00


class TestSonyAudioFe2cType30:
    def test_parse_fe2c_type30(self, parser):
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE30},
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_fe2c_type30_frame_type(self, parser):
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE30},
        )
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 0x30


class TestSonyAudioDeviceClassification:
    def test_speaker_from_srs_name(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        )
        result = parser.parse(raw)
        assert result.device_class == "speaker"

    def test_headphones_from_wh_name(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(raw)
        assert result.device_class == "headphones"

    def test_earbuds_from_wf_name(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_WF-1000XM5",
        )
        result = parser.parse(raw)
        assert result.device_class == "earbuds"

    def test_headphones_from_wi_name(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_WI-1000X",
        )
        result = parser.parse(raw)
        assert result.device_class == "headphones"

    def test_model_strips_le_prefix(self, parser):
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "WH-1000XM5"


class TestSonyAudioFmdnDisambiguation:
    def test_rejects_google_fmdn_fe2c_data(self, parser):
        """fe2c data starting with 0x40 is Google FMDN — must NOT be parsed."""
        raw = make_raw(
            service_data={"fe2c": GOOGLE_FMDN_FE2C},
        )
        result = parser.parse(raw)
        assert result is None

    def test_rejects_fmdn_even_with_sony_name(self, parser):
        """Even with Sony-like name, 0x40+ fe2c data should not be parsed as Sony."""
        raw = make_raw(
            service_data={"fe2c": GOOGLE_FMDN_FE2C},
            local_name="LE_SRS-XB33",
        )
        # Should return None or parse only the name, NOT the FMDN data
        result = parser.parse(raw)
        # If it parses at all, the fe2c FMDN data must not appear in metadata
        if result is not None:
            assert result.metadata.get("frame_type") != 0x40


class TestSonyAudioMatching:
    def test_match_on_company_id_only(self, parser):
        """Should match on company_id 0x012D even without fe2c data."""
        raw = make_raw(
            manufacturer_data=SONY_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None

    def test_match_on_fe2c_sony_frame_only(self, parser):
        """Should match on fe2c service data starting with 0x00."""
        raw = make_raw(
            service_data={"fe2c": SONY_FE2C_TYPE00_SIMPLE},
        )
        result = parser.parse(raw)
        assert result is not None

    def test_returns_none_no_match(self, parser):
        """No Sony company_id and no Sony fe2c data."""
        raw = make_raw(
            manufacturer_data=bytes.fromhex("e000aabbccdd"),
            local_name="Some Device",
        )
        assert parser.parse(raw) is None

    def test_returns_none_empty(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        """Different company ID should not match."""
        wrong_mfr = bytearray(SONY_MFR_DATA)
        wrong_mfr[0] = 0xFF
        wrong_mfr[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(wrong_mfr))
        assert parser.parse(raw) is None


class TestSonyAudioIdentity:
    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(
            manufacturer_data=SONY_MFR_DATA,
            mac_address="AA:BB:CC:DD:EE:FF",
        ))
        r2 = parser.parse(make_raw(
            manufacturer_data=SONY_MFR_DATA,
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash

    def test_same_mac_same_hash(self, parser):
        r1 = parser.parse(make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        ))
        r2 = parser.parse(make_raw(
            manufacturer_data=SONY_MFR_DATA,
            local_name="LE_SRS-XB33",
        ))
        assert r1.identifier_hash == r2.identifier_hash
