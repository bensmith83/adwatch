"""Tests for Oral-B Toothbrush BLE parser plugin.

Byte layout per apk-ble-hunting/reports/pg-oralb-oralbapp_passive.md. The
earlier test file tested a self-consistent but incorrect byte layout (fields
were shifted by 2 bytes). The layout below matches the P&G Advertisement.java
field map.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.oralb import OralBParser, DEVICE_TYPES, DEVICE_STATES


@pytest.fixture
def parser():
    return OralBParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data, local_name=local_name, **defaults
    )


COMPANY_ID_BYTES = bytes([0xDC, 0x00])  # 0x00DC little-endian (P&G / Oral-B)


def _build_oralb(
    *,
    protocol_version=0x02,
    device_type=0x20,          # D701_X_MODE (iO X)
    software_version=0x10,
    device_state=0x03,         # RUN
    status=0x00,               # no pressure / no button presses
    brush_time_min=0,
    brush_time_sec=0,
    brush_mode=0x01,
    brush_progress=0x00,
    quadrant=0x00,
    total_quadrants=0x04,
):
    """Build manufacturer_data: company_id(2) + 11-byte payload per passive report."""
    payload = bytes([
        protocol_version, device_type, software_version, device_state, status,
        brush_time_min, brush_time_sec, brush_mode, brush_progress,
        quadrant, total_quadrants,
    ])
    return COMPANY_ID_BYTES + payload


ORALB_RUNNING = _build_oralb(device_state=0x03, brush_time_min=1, brush_time_sec=30, brush_mode=0x01)
ORALB_IDLE = _build_oralb(device_state=0x02)
ORALB_CHARGING = _build_oralb(device_state=0x04)

WRONG_COMPANY_DATA = bytes([0x4C, 0x00]) + b"\x00" * 11


class TestOralBDeviceState:
    def test_idle(self, parser):
        raw = make_raw(manufacturer_data=ORALB_IDLE, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_state"] == "IDLE"

    def test_running(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["device_state"] == "RUN"

    def test_charging(self, parser):
        raw = make_raw(manufacturer_data=ORALB_CHARGING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["device_state"] == "CHARGE"

    def test_post_brushing_statistics(self, parser):
        data = _build_oralb(device_state=0x0A)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["device_state"] == "POST_BRUSHING_STATISTICS"

    def test_pause(self, parser):
        data = _build_oralb(device_state=0x09)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["device_state"] == "PAUSE"

    def test_sleep(self, parser):
        data = _build_oralb(device_state=0x73)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["device_state"] == "SLEEP"

    def test_unknown_state_code(self, parser):
        data = _build_oralb(device_state=0xAA)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["device_state"].startswith("UNKNOWN_0x")


class TestOralBDeviceType:
    def test_io_x(self, parser):
        data = _build_oralb(device_type=0x20)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "D701_X_MODE"

    def test_genius_x(self, parser):
        data = _build_oralb(device_type=0x00)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "D36_X_MODE"

    def test_sonos_io_g5(self, parser):
        data = _build_oralb(device_type=0x35)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "SONOS_G5"

    def test_smart_series_4_mode(self, parser):
        data = _build_oralb(device_type=0x41)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "D21_4_MODE"

    def test_unknown_device_type(self, parser):
        data = _build_oralb(device_type=0x99)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["device_type"].startswith("UNKNOWN_0x")


class TestOralBStatusByte:
    def test_high_pressure_bit(self, parser):
        data = _build_oralb(status=0x80)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["pressure_high"] is True

    def test_no_pressure(self, parser):
        data = _build_oralb(status=0x00)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["pressure_high"] is False

    def test_power_button(self, parser):
        data = _build_oralb(status=0x08)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["power_button_pressed"] is True

    def test_mode_button(self, parser):
        data = _build_oralb(status=0x04)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["mode_button_pressed"] is True


class TestOralBBrushingTime:
    def test_zero_time(self, parser):
        raw = make_raw(manufacturer_data=_build_oralb(brush_time_min=0, brush_time_sec=0))
        result = parser.parse(raw)
        assert result.metadata["brushing_time_seconds"] == 0

    def test_two_minutes_thirty(self, parser):
        raw = make_raw(manufacturer_data=_build_oralb(brush_time_min=2, brush_time_sec=30))
        result = parser.parse(raw)
        assert result.metadata["brushing_time_seconds"] == 150

    def test_one_minute_thirty(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        result = parser.parse(raw)
        assert result.metadata["brushing_time_seconds"] == 90


class TestOralBProtocolVersion:
    def test_protocol_v2(self, parser):
        raw = make_raw(manufacturer_data=_build_oralb(protocol_version=0x02))
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == 2


class TestOralBFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.parser_name == "oralb"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        result = parser.parse(raw)
        assert result.beacon_type == "oralb"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        result = parser.parse(raw)
        expected = ORALB_RUNNING[2:].hex()
        assert result.raw_payload_hex == expected


class TestOralBIdentity:
    def test_identity_hash_from_mac(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestOralBRejectsInvalid:
    def test_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_empty_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=b"")
        assert parser.parse(raw) is None

    def test_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=WRONG_COMPANY_DATA)
        assert parser.parse(raw) is None

    def test_too_short_payload(self, parser):
        # Company ID + only 4 bytes (need >=5)
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES + b"\x02\x20\x10\x03")
        assert parser.parse(raw) is None

    def test_company_id_only(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES)
        assert parser.parse(raw) is None


class TestOralBRegistration:
    def test_registered_with_company_id(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        reg.register(
            name="oralb",
            company_id=0x00DC,
            local_name_pattern=r"Oral-B",
            description="Oral-B Toothbrush",
            version="2.0.0",
            core=False,
            instance=OralBParser(),
        )
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        assert any(isinstance(p, OralBParser) for p in reg.match(raw))

    def test_registered_matches_local_name(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        reg.register(
            name="oralb",
            company_id=0x00DC,
            local_name_pattern=r"Oral-B",
            description="Oral-B Toothbrush",
            version="2.0.0",
            core=False,
            instance=OralBParser(),
        )
        raw = make_raw(manufacturer_data=None, local_name="Oral-B Toothbrush")
        assert any(isinstance(p, OralBParser) for p in reg.match(raw))
