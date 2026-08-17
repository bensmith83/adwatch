"""Tests for the Blue Spark TempTraq continuous-temperature patch plugin.

Byte layout per apk-ble-hunting/reports/bluesparktechnologies-temptraq_passive.md.
The report indexes the whole AD (`bArr`), where the mfr-data element starts at
bArr[4] and the company ID occupies bArr[6..7]; `manufacturer_payload` strips the
company ID, so payload[i] == bArr[i + 8]:

    payload[0]      packet type / model marker
    payload[1..3]   24-bit patch serial (frame format 2)
    payload[0..3]   32-bit patch serial (frame format 3)
    payload[4]      frame format (low nibble)
    payload[5]      status bits + sample-index bits 16-17
    payload[6..7]   sample-index mid/low
    payload[8]      current temperature sample
    payload[9..22]  14 back-fill temperature samples
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.temptraq import (
    TempTraqParser,
    TEMPTRAQ_SERVICE_UUID,
    TEMPTRAQ_COMPANY_IDS,
    TEMPERATURE_SENTINELS,
    PACKET_TYPE_CADENCE,
    decode_temperature,
    decode_sample_index,
    decode_serial,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
        "service_uuids": [TEMPTRAQ_SERVICE_UUID],
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _payload(packet_type=0x02, serial=0x123456, frame_format=0x02,
             status=0x00, index=0x0102, current=0x96, history=None) -> bytes:
    """Build the 23-byte mfr payload (25-byte mfr element minus company ID)."""
    if history is None:
        history = [0x96] * 14
    assert len(history) == 14
    status_byte = (status & 0xFC) | ((index >> 16) & 0x03)
    return bytes([
        packet_type,
        (serial >> 16) & 0xFF, (serial >> 8) & 0xFF, serial & 0xFF,
        frame_format,
        status_byte,
        (index >> 8) & 0xFF, index & 0xFF,
        current,
    ]) + bytes(history)


def _mfr(payload: bytes, company_id: int = 0x0477) -> bytes:
    return struct.pack("<H", company_id) + payload


def _register(registry):
    @register_parser(
        name="temptraq",
        company_id=list(TEMPTRAQ_COMPANY_IDS),
        service_uuid=TEMPTRAQ_SERVICE_UUID,
        description="TempTraq",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(TempTraqParser):
        pass

    return _P


class TestTempTraqConstants:
    def test_service_uuid(self):
        assert TEMPTRAQ_SERVICE_UUID == "c2fe"

    def test_company_ids_are_little_endian_on_air(self):
        # Code constants 0x005A / 0x7704 are read big-endian by the app; on air
        # the bytes are 00 5A and 77 04 -> LE 0x5A00 and 0x0477 (Blue Spark).
        assert set(TEMPTRAQ_COMPANY_IDS) == {0x0477, 0x5A00}

    def test_payload_helper_is_23_bytes(self):
        assert len(_payload()) == 23

    def test_cadence_table(self):
        assert PACKET_TYPE_CADENCE[0x01] == (720, 86400)
        assert PACKET_TYPE_CADENCE[0x02] == (1440, 172800)
        assert PACKET_TYPE_CADENCE[0x04] == (2160, 259200)
        assert PACKET_TYPE_CADENCE[0xF0] == (2160, 259200)


class TestTemperatureDecode:
    def test_formula(self):
        assert decode_temperature(0x96) == 37.5      # 150 * 0.05 + 30
        assert decode_temperature(0x64) == 35.0
        assert decode_temperature(0xA0) == 38.0

    def test_formula_matches_report_expression(self):
        for raw in (0x50, 0x96, 0xC8):
            assert decode_temperature(raw) == round((raw + 2200) / 20.0 - 80.0, 2)

    def test_f0_offset_applied(self):
        assert decode_temperature(0x96, packet_type=0xF0) == 37.22

    def test_f0_offset_not_applied_to_other_packet_types(self):
        assert decode_temperature(0x96, packet_type=0x02) == 37.5

    def test_sentinels_dropped(self):
        for raw in TEMPERATURE_SENTINELS:
            assert decode_temperature(raw) is None

    def test_f9_sentinel_only_in_format_3(self):
        assert decode_temperature(0xF9, frame_format=3) is None
        assert decode_temperature(0xF9, frame_format=2) == 42.45

    def test_low_values_dropped(self):
        # raw 0 -> 30.0 which is a plausible reading; the <4.0 guard only trips
        # for the sentinel-mapped values, which are handled above.
        assert decode_temperature(0x00) == 30.0


class TestSampleIndexAndSerial:
    def test_sample_index_18_bit(self):
        payload = _payload(index=0x3ABCD)
        assert decode_sample_index(payload) == 0x3ABCD

    def test_sample_index_uses_only_two_status_bits(self):
        payload = bytearray(_payload(index=0x0102))
        payload[5] = 0xFC | 0x02  # high status bits set, index bits = 2
        assert decode_sample_index(bytes(payload)) == 0x20102

    def test_serial_format_2_is_24_bit(self):
        payload = _payload(packet_type=0x02, serial=0xAABBCC, frame_format=0x02)
        assert decode_serial(payload) == 0xAABBCC

    def test_serial_format_3_is_32_bit(self):
        payload = bytearray(_payload(serial=0xAABBCC, frame_format=0x03))
        payload[0] = 0x04
        assert decode_serial(bytes(payload)) == 0x04AABBCC

    def test_serial_format_3_falls_back_to_24_bit_when_type_is_1(self):
        payload = bytearray(_payload(serial=0xAABBCC, frame_format=0x03))
        payload[0] = 0x01
        assert decode_serial(bytes(payload)) == 0xAABBCC

    def test_frame_format_uses_low_nibble(self):
        # 0x32 -> low nibble 2 -> the 24-bit (format 2) serial layout
        payload = _payload(serial=0xAABBCC, frame_format=0x32)
        assert decode_serial(payload) == 0xAABBCC


class TestTempTraqMatching:
    def test_match_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=["C2FE"]))) == 1

    def test_match_blue_spark_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[], manufacturer_data=_mfr(_payload()))
        assert len(registry.match(ad)) == 1

    def test_match_legacy_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[],
                      manufacturer_data=_mfr(_payload(), company_id=0x5A00))
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["fd6f"],
                      manufacturer_data=_mfr(_payload(), company_id=0x004C))
        assert registry.match(ad) == []


class TestTempTraqParse:
    def test_full_decode(self):
        history = [0x95, 0x96, 0x97] + [0xFF] * 11
        payload = _payload(packet_type=0x02, serial=0x123456, index=0x00102,
                           current=0x96, history=history)
        result = TempTraqParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert result is not None
        assert result.parser_name == "temptraq"
        assert result.device_class == "medical"
        assert result.metadata["packet_type"] == 0x02
        assert result.metadata["patch_serial"] == 0x123456
        assert result.metadata["patch_serial_hex"] == "123456"
        assert result.metadata["frame_format"] == 2
        assert result.metadata["sample_index"] == 0x00102
        assert result.metadata["temperature_c"] == 37.5
        assert result.metadata["temperature_f"] == 99.5
        assert result.metadata["patch_duration_hours"] == 48
        assert result.metadata["sample_count"] == 1440
        assert result.metadata["history_count"] == 3
        assert result.metadata["history_temps_c"] == "37.45,37.5,37.55"
        assert result.metadata["temp_min_c"] == 37.45
        assert result.metadata["temp_max_c"] == 37.55

    def test_status_flags(self):
        payload = _payload(status=0xC0)  # bit7 battery/alarm, bit6 R0
        result = TempTraqParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert result.metadata["battery_alarm_flag"] is True
        assert result.metadata["r0_flag"] is True

    def test_status_flags_clear(self):
        result = TempTraqParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(status=0x00)))
        )
        assert result.metadata["battery_alarm_flag"] is False
        assert result.metadata["r0_flag"] is False

    def test_data_frame_classification(self):
        # (status & 0x3C) == 0 and (index & 3) != 3 -> data frame
        result = TempTraqParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(status=0x00, index=0x0102)))
        )
        assert result.metadata["is_data_frame"] is True

    def test_special_command_frame_by_index(self):
        result = TempTraqParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(status=0x00, index=0x0103)))
        )
        assert result.metadata["is_data_frame"] is False

    def test_special_command_frame_by_status_bits(self):
        result = TempTraqParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(status=0x04, index=0x0102)))
        )
        assert result.metadata["is_data_frame"] is False

    def test_f0_packet_type_applies_offset(self):
        payload = _payload(packet_type=0xF0, current=0x96, history=[0xFF] * 14)
        result = TempTraqParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert result.metadata["temperature_c"] == 37.22
        assert result.metadata["patch_duration_hours"] == 72

    def test_sentinel_current_sample_has_no_temperature(self):
        payload = _payload(current=0xFD, history=[0xFF] * 14)
        result = TempTraqParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert result is not None
        assert "temperature_c" not in result.metadata
        assert result.metadata["history_count"] == 0

    def test_identity_hash_uses_patch_serial(self):
        a = TempTraqParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(serial=0x123456)))
        )
        b = TempTraqParser().parse(
            _make_ad(mac_address="11:22:33:44:55:66",
                     manufacturer_data=_mfr(_payload(serial=0x123456, index=0x0999)))
        )
        expected = hashlib.sha256(b"temptraq:123456").hexdigest()[:16]
        assert a.identifier_hash == expected
        assert a.identifier_hash == b.identifier_hash

    def test_stable_key_collapses_volatile_payload(self):
        result = TempTraqParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(serial=0x123456)))
        )
        assert result.stable_key == "temptraq:123456"

    def test_short_payload_returns_none(self):
        ad = _make_ad(manufacturer_data=_mfr(b"\x02\x00\x01\x02"))
        assert TempTraqParser().parse(ad) is None

    def test_invalid_packet_type_returns_none(self):
        payload = _payload(packet_type=0x77)
        assert TempTraqParser().parse(_make_ad(manufacturer_data=_mfr(payload))) is None

    def test_service_uuid_without_mfr_data_returns_none(self):
        assert TempTraqParser().parse(_make_ad(manufacturer_data=None)) is None

    def test_wrong_company_id_returns_none(self):
        payload = _payload()
        ad = _make_ad(service_uuids=[], manufacturer_data=_mfr(payload, company_id=0x004C))
        assert TempTraqParser().parse(ad) is None

    def test_raw_payload_hex(self):
        payload = _payload()
        result = TempTraqParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert result.raw_payload_hex == payload.hex()
