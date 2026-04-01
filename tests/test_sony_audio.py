"""Tests for Sony Audio BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.sony_audio import SonyAudioParser, SONY_COMPANY_ID, SONY_NAME_RE, DEVICE_CLASS_MAP


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
        name="sony_audio",
        company_id=SONY_COMPANY_ID,
        local_name_pattern=r"^LE_(SRS|WF|WH|WI)-",
        description="Sony Audio devices (speakers, headphones, earbuds)",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(SonyAudioParser):
        pass

    return registry


def _sony_mfr_data(version=0x01, device_type=0x02, model_id=0x03, extra=b""):
    """Build manufacturer data: company_id (LE) + version + device_type + model_id + extra."""
    return SONY_COMPANY_ID.to_bytes(2, "little") + bytes([version, device_type, model_id]) + extra


class TestSonyAudioParser:
    def test_matches_company_id(self):
        """Matches on Sony company_id 0x012D."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_WH-1000XM5",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name matching LE_(SRS|WF|WH|WI)-*."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_SRS-XB43",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_parse_with_manufacturer_data(self):
        """Parses manufacturer data extracting version, device_type, model_id."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(version=0x05, device_type=0x0A, model_id=0x1F),
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "sony_audio"
        assert result.metadata["version"] == 0x05
        assert result.metadata["device_type"] == 0x0A
        assert result.metadata["model_id"] == 0x1F

    def test_parse_with_fe2c_service_data(self):
        """Parses fe2c service data with frame type."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": bytes([0x00, 0x30, 0xAB, 0xCD])},
            local_name="LE_WF-1000XM4",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == 0x30
        assert result.metadata["sub_type"] == 0x30

    def test_fe2c_frame_type_below_0x40(self):
        """Frame byte < 0x40 is used as both frame_type and sub_type."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": bytes([0x00, 0x00, 0x01])},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == 0x00
        assert result.metadata["sub_type"] == 0x00

    def test_fe2c_frame_type_above_0x40(self):
        """Frame byte >= 0x80 sets frame_type to 0x00 and sub_type to actual byte."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": bytes([0x00, 0x80, 0x01])},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == 0x00
        assert result.metadata["sub_type"] == 0x80

    def test_fe2c_rejects_fmdn_frames(self):
        """fe2c data with byte[0] >= 0x40 is rejected (FMDN frames)."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": bytes([0x40, 0x01, 0x02])},
        )
        result = parser.parse(ad)
        assert result is None

    def test_fe2c_rejects_short_data(self):
        """fe2c data shorter than 2 bytes is ignored."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": bytes([0x00])},
        )
        result = parser.parse(ad)
        assert result is None

    def test_fe2c_rejects_empty_data(self):
        """Empty fe2c data is ignored."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": b""},
        )
        result = parser.parse(ad)
        assert result is None

    def test_device_class_headphones_wh(self):
        """device_class is 'headphones' for WH- prefix."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(ad)
        assert result.device_class == "headphones"

    def test_device_class_earbuds_wf(self):
        """device_class is 'earbuds' for WF- prefix."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_WF-1000XM4",
        )
        result = parser.parse(ad)
        assert result.device_class == "earbuds"

    def test_device_class_speaker_srs(self):
        """device_class is 'speaker' for SRS- prefix."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_SRS-XB43",
        )
        result = parser.parse(ad)
        assert result.device_class == "speaker"

    def test_device_class_headphones_wi(self):
        """device_class is 'headphones' for WI- prefix."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_WI-C100",
        )
        result = parser.parse(ad)
        assert result.device_class == "headphones"

    def test_device_class_default_audio(self):
        """device_class defaults to 'audio' without matching local_name."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
        )
        result = parser.parse(ad)
        assert result.device_class == "audio"

    def test_device_class_audio_for_non_matching_name(self):
        """device_class is 'audio' when local_name doesn't match the pattern."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="Sony Speaker",
        )
        result = parser.parse(ad)
        assert result.device_class == "audio"

    def test_model_extracted_from_local_name(self):
        """Model name is local_name with 'LE_' prefix stripped."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "WH-1000XM5"

    def test_no_model_without_matching_name(self):
        """No model in metadata when local_name doesn't match."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="Something Else",
        )
        result = parser.parse(ad)
        assert "model" not in result.metadata

    def test_identity_hash_format(self):
        """Identity hash is SHA256('sony_audio:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"sony_audio:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_beacon_type(self):
        """beacon_type is 'sony_audio'."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(),
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(ad)
        assert result.beacon_type == "sony_audio"

    def test_raw_payload_hex_from_manufacturer_data(self):
        """raw_payload_hex is manufacturer_data hex when present."""
        parser = SonyAudioParser()
        mfr = _sony_mfr_data(version=0x01, device_type=0x02, model_id=0x03)
        ad = _make_ad(manufacturer_data=mfr, local_name="LE_WH-1000XM5")
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr.hex()

    def test_raw_payload_hex_from_fe2c_data(self):
        """raw_payload_hex is fe2c service data hex when no manufacturer data."""
        parser = SonyAudioParser()
        fe2c = bytes([0x00, 0x30, 0xAB])
        ad = _make_ad(service_data={"fe2c": fe2c})
        result = parser.parse(ad)
        assert result.raw_payload_hex == fe2c.hex()

    def test_returns_none_for_no_data(self):
        """Returns None when no manufacturer_data and no service_data."""
        parser = SonyAudioParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_wrong_company_id(self):
        """Returns None when company_id doesn't match Sony."""
        parser = SonyAudioParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_short_manufacturer_data(self):
        """Returns None when manufacturer_data is too short (< 2 bytes) and no fe2c."""
        parser = SonyAudioParser()
        ad = _make_ad(manufacturer_data=b"\x2D")
        result = parser.parse(ad)
        assert result is None

    def test_manufacturer_data_exactly_2_bytes(self):
        """Manufacturer data with exactly 2 bytes (company_id only) — no payload fields extracted."""
        parser = SonyAudioParser()
        mfr = SONY_COMPANY_ID.to_bytes(2, "little")
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result is not None
        assert "version" not in result.metadata
        assert "device_type" not in result.metadata

    def test_manufacturer_data_4_bytes_no_model_id(self):
        """Manufacturer data with 4 bytes — version and device_type but model_id is None."""
        parser = SonyAudioParser()
        mfr = SONY_COMPANY_ID.to_bytes(2, "little") + bytes([0x05, 0x0A])
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["version"] == 0x05
        assert result.metadata["device_type"] == 0x0A
        assert result.metadata["model_id"] is None

    def test_both_mfr_and_fe2c(self):
        """When both manufacturer_data and fe2c are present, both are parsed."""
        parser = SonyAudioParser()
        ad = _make_ad(
            manufacturer_data=_sony_mfr_data(version=0x01, device_type=0x02, model_id=0x03),
            service_data={"fe2c": bytes([0x00, 0x30])},
            local_name="LE_WH-1000XM5",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["version"] == 0x01
        assert result.metadata["frame_type"] == 0x30
        assert result.metadata["model"] == "WH-1000XM5"

    def test_raw_payload_hex_prefers_mfr_over_fe2c(self):
        """raw_payload_hex uses manufacturer_data when both are present."""
        parser = SonyAudioParser()
        mfr = _sony_mfr_data()
        ad = _make_ad(
            manufacturer_data=mfr,
            service_data={"fe2c": bytes([0x00, 0x30])},
        )
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr.hex()

    def test_fe2c_frame_byte_exactly_0x3f(self):
        """Frame byte 0x3F (just below 0x40) is treated as its own frame type."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": bytes([0x00, 0x3F])},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["frame_type"] == 0x3F
        assert result.metadata["sub_type"] == 0x3F

    def test_fe2c_none_service_data_value(self):
        """fe2c key exists but value is None — treated as no data."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"fe2c": None},
        )
        result = parser.parse(ad)
        assert result is None

    def test_other_service_data_key_ignored(self):
        """Service data with non-fe2c keys is ignored."""
        parser = SonyAudioParser()
        ad = _make_ad(
            service_data={"abcd": bytes([0x00, 0x01])},
        )
        result = parser.parse(ad)
        assert result is None
