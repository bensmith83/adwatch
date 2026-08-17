"""Tests for iBBQ / EasyBBQ / BBQ Go / GrillEye BBQ thermometer plugin.

Byte layout per apk-ble-hunting reports `easybbq_passive.md` and
`bbqgo_passive.md`. Both reports document offsets relative to the AD
structure's *length* byte (``S``):

    S+0  AD length L   (probe count = (L - 11) / 2)
    S+1  AD type 0xFF
    S+2  sub-opcode  (0x01 temps, 0x02 channel run-time, 0x11/0x12 device-type)
    S+3  header byte
    S+4  header byte
    S+5  flag byte (0x80 QTECH variant / 0x08 confirm-package)
    S+6..S+11  device MAC
    S+12.. 2*N probe fields

``RawAdvertisement.manufacturer_data`` starts at S+2, so the in-payload
header is 10 bytes and the probe fields start at manufacturer_data[10].
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ibbq import (
    IBBQParser,
    IBBQ_HEADER_LEN,
    IBBQ_NAME_PATTERN,
    SUBOP_TEMPERATURES,
    SUBOP_CHANNEL_RUNTIME,
    SUBOP_DEVICE_TYPE_1,
    SUBOP_DEVICE_TYPE_1_ALT,
)


DEFAULT_MAC_BYTES = b"\xff\xee\xdd\xcc\xbb\xaa"


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


def _build_ibbq_mfr_data(values, sub_op=SUBOP_TEMPERATURES, header=b"\x00\x00",
                         flag=0x00, mac_bytes=DEFAULT_MAC_BYTES, signed=True):
    """Build iBBQ manufacturer_data: subop(1)+hdr(2)+flag(1)+mac(6)+fields(2*N)."""
    data = bytes([sub_op]) + header + bytes([flag]) + mac_bytes
    fmt = "<h" if signed else "<H"
    for v in values:
        data += struct.pack(fmt, v)
    return data


def _registered(registry):
    @register_parser(
        name="ibbq",
        local_name_pattern=IBBQ_NAME_PATTERN,
        description="iBBQ",
        version="2.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(IBBQParser):
        pass

    return TestParser


def _parse(ad):
    registry = ParserRegistry()
    _registered(registry)
    matched = registry.match(ad)
    assert len(matched) == 1
    return matched[0].parse(ad)


class TestIBBQLayout:
    def test_header_is_ten_bytes(self):
        """manufacturer_data header is 10 bytes: subop+2 hdr+flag+6 MAC."""
        assert IBBQ_HEADER_LEN == 10

    def test_probe_count_from_data_length(self):
        """Two bytes per probe on top of the 10-byte header."""
        assert len(_build_ibbq_mfr_data([100, 200])) == 14
        assert len(_build_ibbq_mfr_data([100, 200, 300, 400])) == 18
        assert len(_build_ibbq_mfr_data([100, 200, 300, 400, 500, 600])) == 22


class TestIBBQTemperatures:
    def test_two_probe_model(self):
        """IBT-2X: 2 temps decoded from manufacturer_data offset 10."""
        mfr_data = _build_ibbq_mfr_data([250, 305])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")
        result = _parse(ad)
        assert result is not None
        assert result.parser_name == "ibbq"
        assert result.beacon_type == "ibbq"
        assert result.device_class == "sensor"
        assert result.metadata["probe_count"] == 2
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert result.metadata["probe_2_temp_c"] == 30.5

    def test_four_probe_model(self):
        mfr_data = _build_ibbq_mfr_data([250, 305, 100, 450])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["probe_count"] == 4
        assert result.metadata["probe_3_temp_c"] == 10.0
        assert result.metadata["probe_4_temp_c"] == 45.0

    def test_six_probe_model(self):
        mfr_data = _build_ibbq_mfr_data([250, 305, 100, 450, 200, 550])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["probe_count"] == 6
        assert result.metadata["probe_5_temp_c"] == 20.0
        assert result.metadata["probe_6_temp_c"] == 55.0

    def test_disconnected_probe_sentinel_fff6(self):
        """0xFFF6 (-10 raw, -1.0 after /10) = probe absent -> key omitted."""
        mfr_data = _build_ibbq_mfr_data([250, -10])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert "probe_2_temp_c" not in result.metadata

    def test_disconnected_probe_sentinel_ffff(self):
        """0xFFFF (-1 raw) is the other documented no-probe sentinel."""
        mfr_data = _build_ibbq_mfr_data([250, -1])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert "probe_2_temp_c" not in result.metadata

    def test_negative_temperature(self):
        mfr_data = _build_ibbq_mfr_data([-50, 100])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["probe_1_temp_c"] == -5.0
        assert result.metadata["probe_2_temp_c"] == 10.0

    def test_legacy_subop_zero_still_decodes_temps(self):
        """Legacy MyBbqBleService path ignores the sub-opcode byte."""
        mfr_data = _build_ibbq_mfr_data([250, 305], sub_op=0x00)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert result.metadata["sub_op"] == 0x00


class TestIBBQSubOpcodes:
    def test_sub_op_recorded(self):
        mfr_data = _build_ibbq_mfr_data([250])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["sub_op"] == SUBOP_TEMPERATURES
        assert result.metadata["sub_op_name"] == "temperatures"

    def test_channel_runtime(self):
        """sub-op 0x02: u16 per channel, x3 = seconds."""
        mfr_data = _build_ibbq_mfr_data([100, 200], sub_op=SUBOP_CHANNEL_RUNTIME,
                                        signed=False)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="xBBQ"))
        assert result.metadata["sub_op_name"] == "channel_runtime"
        assert result.metadata["probe_1_runtime_s"] == 300
        assert result.metadata["probe_2_runtime_s"] == 600
        assert "probe_1_temp_c" not in result.metadata

    def test_channel_runtime_not_running_sentinel(self):
        mfr_data = _build_ibbq_mfr_data([0xFFFF, 200], sub_op=SUBOP_CHANNEL_RUNTIME,
                                        signed=False)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="xBBQ"))
        assert "probe_1_runtime_s" not in result.metadata
        assert result.metadata["probe_2_runtime_s"] == 600

    def test_device_type_marker_11(self):
        mfr_data = _build_ibbq_mfr_data([], sub_op=SUBOP_DEVICE_TYPE_1)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="xBBQ"))
        assert result is not None
        assert result.metadata["sub_op_name"] == "device_type_marker"
        assert result.metadata["device_type"] == 1

    def test_device_type_marker_12(self):
        mfr_data = _build_ibbq_mfr_data([], sub_op=SUBOP_DEVICE_TYPE_1_ALT)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="xBBQ"))
        assert result.metadata["device_type"] == 1
        assert "probe_1_temp_c" not in result.metadata


class TestIBBQFlagByte:
    def test_qtech_variant_flag(self):
        mfr_data = _build_ibbq_mfr_data([250], flag=0x80)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["qtech_variant"] is True

    def test_confirm_package_flag(self):
        mfr_data = _build_ibbq_mfr_data([250], flag=0x08)
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="xBBQ"))
        assert result.metadata["confirm_package"] is True

    def test_no_flags_by_default(self):
        mfr_data = _build_ibbq_mfr_data([250])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert "qtech_variant" not in result.metadata
        assert "confirm_package" not in result.metadata


class TestIBBQEmbeddedMac:
    def test_device_mac_decoded(self):
        mfr_data = _build_ibbq_mfr_data([250], mac_bytes=b"\x11\x22\x33\x44\x55\x66")
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.metadata["device_mac"] == "11:22:33:44:55:66"

    def test_identity_hash_from_embedded_mac(self):
        """Embedded MAC is stable across BLE MAC randomisation -> identity basis."""
        mfr_data = _build_ibbq_mfr_data([250], mac_bytes=b"\x11\x22\x33\x44\x55\x66")
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ",
                      mac_address="AA:BB:CC:DD:EE:FF")
        result = _parse(ad)
        expected = hashlib.sha256(b"ibbq:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_stable_across_ble_mac(self):
        mfr_data = _build_ibbq_mfr_data([250], mac_bytes=b"\x11\x22\x33\x44\x55\x66")
        a = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ",
                            mac_address="AA:BB:CC:DD:EE:FF"))
        b = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ",
                            mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash == b.identifier_hash

    def test_identity_falls_back_to_ble_mac_when_header_blank(self):
        mfr_data = _build_ibbq_mfr_data([250], mac_bytes=b"\x00" * 6)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ",
                      mac_address="11:22:33:44:55:66")
        result = _parse(ad)
        expected = hashlib.sha256(b"ibbq:mac:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_falls_back_to_ble_mac_when_header_all_ff(self):
        mfr_data = _build_ibbq_mfr_data([250], mac_bytes=b"\xff" * 6)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ",
                      mac_address="11:22:33:44:55:66")
        result = _parse(ad)
        expected = hashlib.sha256(b"ibbq:mac:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self):
        mfr_data = _build_ibbq_mfr_data([250])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestIBBQMatching:
    @pytest.mark.parametrize("name", ["iBBQ", "xBBQ", "GrillEye", "iBBQ-4"])
    def test_matches_known_names(self, name):
        registry = ParserRegistry()
        _registered(registry)
        ad = _make_ad(local_name=name,
                      manufacturer_data=_build_ibbq_mfr_data([100, 200]))
        assert len(registry.match(ad)) == 1

    @pytest.mark.parametrize("name", ["SomeOtherDevice", "BBQ", "MyiBBQ", None])
    def test_does_not_match_other_names(self, name):
        registry = ParserRegistry()
        _registered(registry)
        ad = _make_ad(local_name=name,
                      manufacturer_data=_build_ibbq_mfr_data([100, 200]))
        assert registry.match(ad) == []

    def test_model_recorded_from_name(self):
        mfr_data = _build_ibbq_mfr_data([250])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="GrillEye"))
        assert result.metadata["model"] == "GrillEye"


class TestIBBQRejectsInvalid:
    def test_no_manufacturer_data(self):
        result = _parse(_make_ad(manufacturer_data=None, local_name="iBBQ"))
        assert result is None

    def test_header_too_short(self):
        """Fewer than 10 bytes cannot hold the header."""
        result = _parse(_make_ad(manufacturer_data=b"\x01\x00\x00\x00\x00\x00",
                                 local_name="iBBQ"))
        assert result is None

    def test_temps_subop_without_probe_fields(self):
        """Header only, sub-op 0x01: nothing to report."""
        result = _parse(_make_ad(manufacturer_data=_build_ibbq_mfr_data([]),
                                 local_name="iBBQ"))
        assert result is None

    def test_raw_payload_hex_is_full_manufacturer_data(self):
        mfr_data = _build_ibbq_mfr_data([250])
        result = _parse(_make_ad(manufacturer_data=mfr_data, local_name="iBBQ"))
        assert result.raw_payload_hex == mfr_data.hex()
