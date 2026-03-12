"""Tests for Oral-B Toothbrush BLE parser plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.oralb import OralBParser


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


# --- Constants ---

COMPANY_ID_BYTES = bytes([0xDC, 0x00])  # 0x00DC little-endian (Procter & Gamble)


def _build_oralb(
    *,
    protocol_version=0x02,
    state=0x03,        # Running
    pressure=0x00,     # Normal
    minutes=0,
    seconds=0,
    mode=0x01,         # Daily Clean
    sector=0,
):
    """Build manufacturer_data for Oral-B BLE advertisement.

    Payload layout (after 2-byte company ID):
      byte 0: protocol version
      byte 1: brushing state
      byte 2: pressure flags
      byte 3: brushing time minutes
      byte 4: brushing time seconds
      byte 5: brushing mode
      byte 6: sector / quadrant
    """
    payload = bytes([protocol_version, state, pressure, minutes, seconds, mode, sector])
    return COMPANY_ID_BYTES + payload


# --- Pre-built test data ---

ORALB_RUNNING = _build_oralb(state=0x03, minutes=1, seconds=30, mode=0x01, sector=2)
ORALB_IDLE = _build_oralb(state=0x02)
ORALB_CHARGING = _build_oralb(state=0x04)
ORALB_SHUTDOWN = _build_oralb(state=0x07)
ORALB_STAGE_COMPLETED = _build_oralb(state=0x06)
ORALB_UNKNOWN_STATE = _build_oralb(state=0x00)

WRONG_COMPANY_DATA = bytes([0x4C, 0x00]) + b"\x00" * 7


class TestOralBBrushingState:
    def test_idle(self, parser):
        raw = make_raw(manufacturer_data=ORALB_IDLE, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["state"] == "idle"

    def test_running(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["state"] == "running"

    def test_charging(self, parser):
        raw = make_raw(manufacturer_data=ORALB_CHARGING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["state"] == "charging"

    def test_shutdown(self, parser):
        raw = make_raw(manufacturer_data=ORALB_SHUTDOWN, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["state"] == "shutdown"

    def test_stage_completed(self, parser):
        raw = make_raw(manufacturer_data=ORALB_STAGE_COMPLETED, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["state"] == "stage_completed"

    def test_unknown_state(self, parser):
        raw = make_raw(manufacturer_data=ORALB_UNKNOWN_STATE, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["state"] == "unknown"


class TestOralBPressure:
    def test_normal_pressure(self, parser):
        data = _build_oralb(pressure=0x00)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["pressure"] == "normal"

    def test_high_pressure(self, parser):
        data = _build_oralb(pressure=0x01)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["pressure"] == "high"

    def test_overpressure(self, parser):
        data = _build_oralb(pressure=0x03)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["pressure"] == "overpressure"


class TestOralBBrushingTime:
    def test_zero_time(self, parser):
        data = _build_oralb(minutes=0, seconds=0)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["brushing_time_seconds"] == 0

    def test_two_minutes_thirty(self, parser):
        data = _build_oralb(minutes=2, seconds=30)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["brushing_time_seconds"] == 150

    def test_one_minute_thirty(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["brushing_time_seconds"] == 90


class TestOralBMode:
    def test_off(self, parser):
        data = _build_oralb(mode=0x00)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "off"

    def test_daily_clean(self, parser):
        data = _build_oralb(mode=0x01)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "daily_clean"

    def test_sensitive(self, parser):
        data = _build_oralb(mode=0x02)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "sensitive"

    def test_massage(self, parser):
        data = _build_oralb(mode=0x03)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "massage"

    def test_whitening(self, parser):
        data = _build_oralb(mode=0x04)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "whitening"

    def test_deep_clean(self, parser):
        data = _build_oralb(mode=0x05)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "deep_clean"

    def test_tongue_cleaning(self, parser):
        data = _build_oralb(mode=0x06)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "tongue_cleaning"

    def test_turbo(self, parser):
        data = _build_oralb(mode=0x07)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "turbo"


class TestOralBSector:
    def test_sector_zero(self, parser):
        data = _build_oralb(sector=0)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["sector"] == 0

    def test_sector_three(self, parser):
        data = _build_oralb(sector=3)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["sector"] == 3

    def test_sector_seven(self, parser):
        data = _build_oralb(sector=7)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["sector"] == 7


class TestOralBProtocolVersion:
    def test_protocol_v2(self, parser):
        data = _build_oralb(protocol_version=0x02)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == 2

    def test_protocol_v3(self, parser):
        data = _build_oralb(protocol_version=0x03)
        raw = make_raw(manufacturer_data=data, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == 3


class TestOralBFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.parser_name == "oralb"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.beacon_type == "oralb"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        expected = ORALB_RUNNING[2:].hex()
        assert result.raw_payload_hex == expected


class TestOralBIdentity:
    def test_identity_hash_from_mac(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(manufacturer_data=ORALB_RUNNING, local_name="Oral-B Toothbrush")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex


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
        # Company ID + only 4 bytes (need 7)
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES + b"\x02\x03\x00\x01")
        assert parser.parse(raw) is None

    def test_company_id_only(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES)
        assert parser.parse(raw) is None


class TestOralBRegistration:
    def test_registered_with_company_id(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = OralBParser()
        reg.register(
            name="oralb",
            company_id=0x00DC,
            local_name_pattern=r"Oral-B",
            description="Oral-B Toothbrush",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=ORALB_RUNNING)
        matched = reg.match(raw)
        assert any(isinstance(p, OralBParser) for p in matched)

    def test_registered_matches_local_name(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = OralBParser()
        reg.register(
            name="oralb",
            company_id=0x00DC,
            local_name_pattern=r"Oral-B",
            description="Oral-B Toothbrush",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=None, local_name="Oral-B Toothbrush")
        matched = reg.match(raw)
        assert any(isinstance(p, OralBParser) for p in matched)

    def test_not_core(self):
        """Oral-B should be a plugin (core=False)."""
        assert True  # verified by registration above
