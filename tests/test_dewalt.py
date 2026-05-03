"""Tests for DeWalt Tool Connect plugin.

Layouts per apk-ble-hunting/reports/dewalt-toolconnect_passive.md.
"""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.dewalt import (
    DewaltParser,
    DEWALT_COMPANY_ID,
    DEWALT_SERVICE_UUID,
    DIVISION_NAMES,
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
        name="dewalt",
        company_id=DEWALT_COMPANY_ID,
        service_uuid=DEWALT_SERVICE_UUID,
        description="DeWalt",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(DewaltParser):
        pass

    return _P


def _battery_mfr(
    soc_byte=0xF0,         # 15 steps = 100 %
    status_lsb=0x00,
    status_msb=0x00,
    firmware=0x21,         # major=1, minor=1
    temp=65,               # 65 - 40 = 25 °C
    voltage=200,           # 200 / 10 = 20 V
    usage=42,
    impedance=10,
    capacity_hi=0x12,
    capacity_lo=0x34,
    v_health=99,
):
    """Build mfr-data with FE 00 CID + 20-byte battery payload."""
    cid = b"\xfe\x00"
    payload = bytes([
        0x00,           # division=battery (mfr[2] / payload[0])
        0x00, 0x00,     # mfr[3..4] reserved
        0x00, 0x00, 0x00, 0x00,  # mfr[5..8] reserved
        soc_byte,       # mfr[9]
        status_lsb,     # mfr[10]
        status_msb,     # mfr[11]
        0x00,           # mfr[12] PairingControlType
        firmware,       # mfr[13]
        temp,           # mfr[14]
        voltage,        # mfr[15]
        usage,          # mfr[16]
        0x00,           # mfr[17] reserved
        impedance,      # mfr[18]
        capacity_hi,    # mfr[19]
        capacity_lo,    # mfr[20]
        v_health,       # mfr[21]
    ])
    return cid + payload


class TestDewaltConstants:
    def test_company_id(self):
        assert DEWALT_COMPANY_ID == 0x00FE

    def test_service_uuid(self):
        assert DEWALT_SERVICE_UUID == "face"

    def test_divisions(self):
        assert DIVISION_NAMES[0x00] == "battery"
        assert DIVISION_NAMES[0x03] == "drill"


class TestDewaltMatching:
    def test_match_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[DEWALT_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_battery_mfr())
        assert len(registry.match(ad)) == 1


class TestDewaltBattery:
    def _parse(self, **kw):
        return DewaltParser().parse(_make_ad(**kw))

    def test_division_decoded(self):
        result = self._parse(manufacturer_data=_battery_mfr())
        assert result.metadata["division"] == "battery"
        assert result.metadata["division_id"] == 0x00

    def test_soc_full_charge(self):
        # SoC byte 0xF0 → 15 steps → 100 %
        result = self._parse(manufacturer_data=_battery_mfr(soc_byte=0xF0))
        assert result.metadata["soc_steps"] == 15
        assert result.metadata["soc_percent"] == 100.0

    def test_soc_half_charge(self):
        # 8 steps → ~53 %
        result = self._parse(manufacturer_data=_battery_mfr(soc_byte=0x80))
        assert result.metadata["soc_steps"] == 8
        assert result.metadata["soc_percent"] == pytest.approx(53.3, abs=0.1)

    def test_status_bits_lsb(self):
        # bit 2 = soc_pushed, bit 5 = enabled
        result = self._parse(manufacturer_data=_battery_mfr(status_lsb=(1 << 2) | (1 << 5)))
        assert result.metadata["status_lsb"]["soc_pushed"] is True
        assert result.metadata["status_lsb"]["enabled"] is True
        assert result.metadata["status_lsb"]["discharging"] is False

    def test_status_bits_msb(self):
        # bit 0 = commissioned, bit 5 = is_charging
        result = self._parse(manufacturer_data=_battery_mfr(status_msb=(1 << 0) | (1 << 5)))
        assert result.metadata["status_msb"]["commissioned"] is True
        assert result.metadata["status_msb"]["is_charging"] is True

    def test_firmware_split(self):
        # 0x21 = 0010_0001 → major = 0b001 = 1, minor = 0b00001 = 1
        result = self._parse(manufacturer_data=_battery_mfr(firmware=0x21))
        assert result.metadata["firmware_major"] == 1
        assert result.metadata["firmware_minor"] == 1

    def test_temperature_offset_minus_40(self):
        result = self._parse(manufacturer_data=_battery_mfr(temp=65))
        assert result.metadata["temperature_c"] == 25

    def test_voltage_div_10(self):
        result = self._parse(manufacturer_data=_battery_mfr(voltage=200))
        assert result.metadata["voltage_v"] == pytest.approx(20.0)

    def test_pti_extraction(self):
        # PTI = (impedance, capacity_hi, status_msb) BE = (0x10, 0x12, 0x00)
        # → 0x101200
        result = self._parse(manufacturer_data=_battery_mfr(
            impedance=0x10, capacity_hi=0x12, status_msb=0x00,
        ))
        assert result.metadata["pti"] == 0x101200
        assert result.metadata["pti_hex"] == "101200"


class TestDewaltOtherDivisions:
    def test_drill_division(self):
        # 1-byte payload: division=0x03 → drill
        ad = _make_ad(manufacturer_data=b"\xfe\x00\x03")
        result = DewaltParser().parse(ad)
        assert result.metadata["division"] == "drill"
        # No battery decode for non-battery division
        assert "soc_percent" not in result.metadata

    def test_unknown_division_tagged(self):
        ad = _make_ad(manufacturer_data=b"\xfe\x00\x77")
        result = DewaltParser().parse(ad)
        assert result.metadata["division"] == "unknown_119"


class TestDewaltBasics:
    def test_returns_none_unrelated(self):
        assert DewaltParser().parse(_make_ad()) is None

    def test_parse_result_basics(self):
        ad = _make_ad(manufacturer_data=_battery_mfr())
        result = DewaltParser().parse(ad)
        assert result.parser_name == "dewalt"
        assert result.device_class == "power_tool"
