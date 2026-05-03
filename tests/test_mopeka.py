"""Tests for Mopeka tank-level sensor plugin.

Byte layouts per apk-ble-hunting/reports/mopeka-tankcheck_passive.md.

The framework treats bytes 0-1 of manufacturer_data as a CID (so
manufacturer_payload starts at the report's byte[2]). Tests build
mfr-data with a 2-byte CID prefix and the documented byte order.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.mopeka import (
    MopekaParser,
    MOPEKA_NRF52_UUID,
    MOPEKA_CC2540_UUID,
    MOPEKA_GATEWAY_UUID,
    NRF52_HW_VARIANTS,
    QUALITY_LABELS,
)


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


def _register(registry):
    @register_parser(
        name="mopeka",
        service_uuid=(MOPEKA_NRF52_UUID, MOPEKA_CC2540_UUID, MOPEKA_GATEWAY_UUID),
        description="Mopeka",
        version="2.0.0",
        core=False,
        registry=registry,
    )
    class _P(MopekaParser):
        pass

    return _P


def _nrf52_mfr(
    hw_byte=0x03,         # PRO_MOPEKA, extended_range=False
    battery_byte=64,
    temp_byte=65,         # 65 - 40 = 25 °C, sync clear
    level_word=1234,      # quality 0
    mac_tail=b"\x11\x22\x33",
    accel_x=0,
    accel_y=0,
):
    """Construct a 12-byte mfr-data record (2-byte CID prefix + 10-byte payload)."""
    cid = b"\x00\x59"  # arbitrary — framework strips, parser doesn't validate
    body = bytes([
        hw_byte,
        battery_byte,
        temp_byte,
        level_word & 0xFF,
        (level_word >> 8) & 0xFF,
        mac_tail[0], mac_tail[1], mac_tail[2],
        accel_x & 0xFF,
        accel_y & 0xFF,
    ])
    return cid + body


class TestMopekaConstants:
    def test_nrf52_uuid(self):
        assert MOPEKA_NRF52_UUID == "fee5"

    def test_cc2540_uuid(self):
        assert MOPEKA_CC2540_UUID == "ada0"

    def test_known_hw_variants(self):
        assert NRF52_HW_VARIANTS[259] == "PRO_MOPEKA"
        assert NRF52_HW_VARIANTS[268] == "PRO_UNIVERSAL"


class TestMopekaMatching:
    def test_matches_on_nrf52_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MOPEKA_NRF52_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_on_cc2540_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MOPEKA_CC2540_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_on_gateway_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MOPEKA_GATEWAY_UUID])
        assert len(registry.match(ad)) == 1


class TestNRF52Parsing:
    def _parse(self, **kw):
        ad = _make_ad(service_uuids=[MOPEKA_NRF52_UUID], **kw)
        return MopekaParser().parse(ad)

    def test_hw_variant_decoded(self):
        # hw_byte=0x03 + 0x100 = 0x103 = 259 = PRO_MOPEKA
        result = self._parse(manufacturer_data=_nrf52_mfr(hw_byte=0x03))
        assert result.metadata["hardware_variant"] == "PRO_MOPEKA"
        assert result.metadata["hardware_id"] == 259
        assert result.metadata["extended_range"] is False

    def test_extended_range_flag(self):
        # bit 7 set
        result = self._parse(manufacturer_data=_nrf52_mfr(hw_byte=0x83))
        assert result.metadata["extended_range"] is True
        assert result.metadata["hardware_id"] == 259

    def test_battery_voltage_formula(self):
        # battery_byte=64 → 64/32 = 2.0 V
        result = self._parse(manufacturer_data=_nrf52_mfr(battery_byte=64))
        assert result.metadata["battery_voltage"] == pytest.approx(2.0)

    def test_temperature_offset_minus_40(self):
        # temp byte 65 (low 7 bits) → 65 - 40 = 25 °C
        result = self._parse(manufacturer_data=_nrf52_mfr(temp_byte=65))
        assert result.metadata["temperature_c"] == 25
        assert result.metadata["sync_pressed"] is False

    def test_temperature_below_zero(self):
        # 30 - 40 = -10 °C
        result = self._parse(manufacturer_data=_nrf52_mfr(temp_byte=30))
        assert result.metadata["temperature_c"] == -10

    def test_sync_button_bit(self):
        # bit 7 of temp byte = sync flag; set bit 7 + temp 25
        result = self._parse(manufacturer_data=_nrf52_mfr(temp_byte=0x80 | 65))
        assert result.metadata["sync_pressed"] is True
        assert result.metadata["temperature_c"] == 25

    def test_level_quality_high(self):
        # level_word top 2 bits = 3 → "high"
        result = self._parse(manufacturer_data=_nrf52_mfr(level_word=(3 << 14) | 100))
        assert result.metadata["quality_stars"] == 3
        assert result.metadata["reading_quality"] == "high"

    def test_level_quality_no_reading(self):
        result = self._parse(manufacturer_data=_nrf52_mfr(level_word=0))
        assert result.metadata["reading_quality"] == "no_reading"

    def test_level_meters_normal_range(self):
        # raw 1000 * 1e-6 = 0.001 m, quality=0
        result = self._parse(manufacturer_data=_nrf52_mfr(level_word=1000))
        assert result.metadata["level_meters"] == pytest.approx(0.001)

    def test_level_meters_extended_range(self):
        # extended_range bit + raw 1000 → (16384 + 1000*4) * 1e-6
        result = self._parse(manufacturer_data=_nrf52_mfr(hw_byte=0x83, level_word=1000))
        expected = (16384 + 1000 * 4) * 1e-6
        assert result.metadata["level_meters"] == pytest.approx(expected)

    def test_mac_tail_extracted(self):
        result = self._parse(manufacturer_data=_nrf52_mfr(mac_tail=b"\xab\xcd\xef"))
        assert result.metadata["mac_tail_hex"] == "abcdef"

    def test_accelerometer_signed(self):
        # 0x80 = -128 / 16 = -8.0
        result = self._parse(manufacturer_data=_nrf52_mfr(accel_x=0x80, accel_y=0x10))
        assert result.metadata["accel_x"] == pytest.approx(-8.0)
        assert result.metadata["accel_y"] == pytest.approx(1.0)

    def test_family_tag(self):
        result = self._parse(manufacturer_data=_nrf52_mfr())
        assert result.metadata["family"] == "nrf52"


class TestCC2540Parsing:
    def _parse(self, payload_post_cid: bytes):
        cid = b"\x00\x00"
        ad = _make_ad(
            service_uuids=[MOPEKA_CC2540_UUID],
            manufacturer_data=cid + payload_post_cid,
        )
        return MopekaParser().parse(ad)

    def test_no_data_sentinel(self):
        # payload[0] (= report's byte[2]) == 0xAA → no-data marker
        payload = b"\xaa" + bytes(19)
        result = self._parse(payload)
        assert result.metadata.get("no_data_sentinel") is True

    def test_battery_formula(self):
        # accel byte, hw byte, battery=128, temp byte, then 16-byte echo list
        payload = bytes([0x00, 0x00, 128, 50]) + bytes(16)
        result = self._parse(payload)
        # battery_voltage = 128/256 * 2 + 1.5 = 2.5
        assert result.metadata["battery_voltage"] == pytest.approx(2.5)

    def test_temperature_zero_raw_is_minus_40(self):
        payload = bytes([0x00, 0x00, 100, 0]) + bytes(16)
        result = self._parse(payload)
        assert result.metadata["temperature_c"] == -40

    def test_corrupted_sentinel(self):
        # battery==0xFF AND temp byte==0x3F → corrupted flag
        payload = bytes([0x00, 0x00, 0xFF, 0x3F]) + bytes(16)
        result = self._parse(payload)
        assert result.metadata.get("corrupted") is True

    def test_bmpro_quality_in_hw_byte(self):
        # hw byte 0x46 (=70) with quality 3 in bits 4-5: (3 << 4) | 70 = 0x76
        payload = bytes([0x00, 0x76, 100, 50]) + bytes(16)
        result = self._parse(payload)
        # 0x76 & 0xCF = 0x46 = 70
        assert result.metadata["hardware_id"] == 70
        assert result.metadata["quality_stars"] == 3
        assert result.metadata["reading_quality"] == "high"

    def test_echo_list_preserved_as_hex(self):
        echo = bytes(range(16))
        payload = bytes([0x00, 0x00, 100, 50]) + echo
        result = self._parse(payload)
        assert result.metadata["echo_list_hex"] == echo.hex()

    def test_mac_tail_when_25_bytes(self):
        # 23-byte payload (post-CID) → MAC tail at offsets 20-22
        payload = bytes([0x00, 0x00, 100, 50]) + bytes(16) + b"\xaa\xbb\xcc"
        result = self._parse(payload)
        assert result.metadata["mac_tail_hex"] == "aabbcc"

    def test_family_tag(self):
        payload = bytes([0x00, 0x00, 100, 50]) + bytes(16)
        result = self._parse(payload)
        assert result.metadata["family"] == "cc2540"


class TestGatewayParsing:
    def test_gateway_marker(self):
        # 6-byte mfr-data: CID 0x44 0x2F + 4-byte payload
        ad = _make_ad(
            service_uuids=[MOPEKA_GATEWAY_UUID],
            manufacturer_data=b"\x44\x2f\x00\xaa\xbb\xcc",
        )
        result = MopekaParser().parse(ad)
        assert result.metadata["family"] == "gateway"
        assert result.metadata["product"] == "gateway"
        assert result.metadata["mac_tail_hex"] == "aabbcc"


class TestIdentity:
    def test_identity_uses_mac_tail_when_present(self):
        ad = _make_ad(
            service_uuids=[MOPEKA_NRF52_UUID],
            manufacturer_data=_nrf52_mfr(mac_tail=b"\xde\xad\xbe"),
            mac_address="11:22:33:44:55:66",
        )
        result = MopekaParser().parse(ad)
        expected = hashlib.sha256(b"mopeka:deadbe").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_result_basics(self):
        ad = _make_ad(
            service_uuids=[MOPEKA_NRF52_UUID],
            manufacturer_data=_nrf52_mfr(),
        )
        result = MopekaParser().parse(ad)
        assert result.parser_name == "mopeka"
        assert result.beacon_type == "mopeka"
        assert result.device_class == "sensor"


class TestEdgeCases:
    def test_no_manufacturer_data(self):
        ad = _make_ad(service_uuids=[MOPEKA_NRF52_UUID])
        assert MopekaParser().parse(ad) is None

    def test_short_payload_falls_back_to_length_guess(self):
        # No service UUID present — parser guesses gateway from 4-byte payload.
        ad = _make_ad(manufacturer_data=b"\x44\x2f\x00\xaa\xbb\xcc")
        result = MopekaParser().parse(ad)
        assert result is not None
        assert result.metadata["family"] == "gateway"
