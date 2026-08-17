"""Tests for the ThermoBeacon plugin.

Layout is ground truth from ``reports/watchflower_passive.md`` — WatchFlower is
open source (``src/src/devices/device_thermobeacon.cpp:407-475``,
``src/docs/thermobeacon-ble-api.md``).

Offsets below are relative to ``RawAdvertisement.manufacturer_payload`` (the
company ID is already stripped).
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.thermobeacon import (
    ThermoBeaconParser,
    THERMOBEACON_COMPANY_IDS,
)


MAC_REVERSED = bytes([0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA])  # -> AA:BB:CC:DD:EE:FF


@pytest.fixture
def parser():
    return ThermoBeaconParser()


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
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


def build_live_frame(*, battery_mv=3005, temp_raw=360, humidity_raw=652,
                     uptime_upper=b"\x00\x00\x00", mac=MAC_REVERSED,
                     company_id=0x0010):
    """18-byte live frame.

    ``0 padding(2) | 2 MAC(6) | 8 battery mV(2) | 10 temp int16(2) |
    12 humidity uint16(2) | 13 uptime int32(4)``

    Note the deliberate overlap: the uptime starts at byte 13, which is also
    the humidity's high byte — that is what the WatchFlower source does.
    """
    payload = bytearray(b"\x00\x00") + mac
    payload += struct.pack("<H", battery_mv)
    payload += struct.pack("<h", temp_raw)
    payload += struct.pack("<H", humidity_raw)   # len 14
    payload += uptime_upper                       # bytes 14-16, len 17
    payload += b"\x00"                            # byte 17 unused, len 18
    assert len(payload) == 18
    return struct.pack("<H", company_id) + bytes(payload)


def build_minmax_frame(*, button=False, max_temp_raw=398, time_max=0x001F7A3D,
                       min_temp_raw=334, time_min=0x0006800A,
                       mac=MAC_REVERSED, company_id=0x0010):
    """20-byte min/max frame."""
    payload = bytearray([0x00, 0x80 if button else 0x00]) + mac
    payload += struct.pack("<h", max_temp_raw)
    payload += struct.pack("<i", time_max)
    payload += struct.pack("<h", min_temp_raw)
    payload += struct.pack("<i", time_min)
    assert len(payload) == 20
    return struct.pack("<H", company_id) + bytes(payload)


NORMAL_DATA = build_live_frame()


class TestThermoBeaconLiveFrame:
    def test_parse_valid(self, parser):
        result = parser.parse(make_raw(manufacturer_data=NORMAL_DATA, local_name="TP357"))
        assert result is not None
        assert isinstance(result, ParseResult)
        assert result.parser_name == "thermobeacon"
        assert result.beacon_type == "thermobeacon"
        assert result.device_class == "sensor"
        assert result.metadata["frame_type"] == "live"

    def test_report_worked_example(self, parser):
        """0x0BBD -> 3.005 V, 0x0168 -> 22.5 C, 0x028C -> 40.75 %RH."""
        data = build_live_frame(battery_mv=0x0BBD, temp_raw=0x0168,
                                humidity_raw=0x028C)
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result.metadata["battery_mv"] == 3005
        assert result.metadata["battery_v"] == pytest.approx(3.005)
        assert result.metadata["temperature_c"] == pytest.approx(22.5)
        assert result.metadata["humidity"] == pytest.approx(40.75)

    def test_battery_percent_is_mapped_2300_to_3100(self, parser):
        for mv, pct in ((2300, 0), (3100, 100), (2700, 50)):
            result = parser.parse(make_raw(manufacturer_data=build_live_frame(battery_mv=mv)))
            assert result.metadata["battery_percent"] == pytest.approx(pct, abs=0.6)

    def test_battery_percent_is_clamped(self, parser):
        low = parser.parse(make_raw(manufacturer_data=build_live_frame(battery_mv=1000)))
        high = parser.parse(make_raw(manufacturer_data=build_live_frame(battery_mv=4000)))
        assert low.metadata["battery_percent"] == 0
        assert high.metadata["battery_percent"] == 100

    def test_negative_temperature_is_signed_int16(self, parser):
        """-16/16 = -1.0 C — no magic 4096 wraparound needed."""
        result = parser.parse(make_raw(manufacturer_data=build_live_frame(temp_raw=-16)))
        assert result.metadata["temperature_c"] == pytest.approx(-1.0)

    def test_very_negative_temperature(self, parser):
        result = parser.parse(make_raw(manufacturer_data=build_live_frame(temp_raw=-95)))
        assert result.metadata["temperature_c"] == pytest.approx(-5.9375)

    def test_zero_temperature(self, parser):
        result = parser.parse(make_raw(manufacturer_data=build_live_frame(temp_raw=0)))
        assert result.metadata["temperature_c"] == pytest.approx(0.0)

    def test_uptime_reads_bytes_13_to_16_and_divides_by_256(self, parser):
        # humidity 0x028C puts 0x02 at byte 13; upper bytes make 0x0059BE1C.
        data = build_live_frame(humidity_raw=0x1C8C,
                                uptime_upper=bytes([0xBE, 0x59, 0x00]))
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result.metadata["uptime_seconds"] == 0x0059BE1C // 256

    def test_embedded_mac_is_reported(self, parser):
        result = parser.parse(make_raw(manufacturer_data=NORMAL_DATA))
        assert result.metadata["mac"] == "AA:BB:CC:DD:EE:FF"


class TestThermoBeaconMinMaxFrame:
    def test_minmax_frame_decoded(self, parser):
        result = parser.parse(make_raw(manufacturer_data=build_minmax_frame()))
        assert result is not None
        assert result.metadata["frame_type"] == "minmax"
        assert result.metadata["temperature_max_c"] == pytest.approx(398 / 16)
        assert result.metadata["temperature_min_c"] == pytest.approx(334 / 16)
        assert result.metadata["time_of_max"] == 0x001F7A3D
        assert result.metadata["time_of_min"] == 0x0006800A
        # A min/max frame carries no live reading.
        assert "temperature_c" not in result.metadata

    def test_button_state_bit(self, parser):
        pressed = parser.parse(make_raw(manufacturer_data=build_minmax_frame(button=True)))
        idle = parser.parse(make_raw(manufacturer_data=build_minmax_frame(button=False)))
        assert pressed.metadata["button_pressed"] is True
        assert idle.metadata["button_pressed"] is False

    def test_minmax_frame_has_mac(self, parser):
        result = parser.parse(make_raw(manufacturer_data=build_minmax_frame()))
        assert result.metadata["mac"] == "AA:BB:CC:DD:EE:FF"


class TestThermoBeaconCompanyIds:
    def test_both_company_ids_accepted(self):
        """The report pins 0x0010; 0x0011 is what several units emit in the
        wild, so both are matched."""
        assert set(THERMOBEACON_COMPANY_IDS) == {0x0010, 0x0011}

    @pytest.mark.parametrize("cid", [0x0010, 0x0011])
    def test_parses_each_company_id(self, parser, cid):
        data = build_live_frame(company_id=cid)
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result is not None
        assert result.metadata["company_id"] == cid

    def test_wrong_company_id_rejected(self, parser):
        data = build_live_frame(company_id=0x004C)
        assert parser.parse(make_raw(manufacturer_data=data)) is None


class TestThermoBeaconIdentity:
    def test_identity_uses_embedded_mac(self, parser):
        """The payload MAC survives BLE MAC rotation, so it anchors identity."""
        expected = hashlib.sha256(b"thermobeacon:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        a = parser.parse(make_raw(manufacturer_data=NORMAL_DATA,
                                  mac_address="00:00:00:00:00:01"))
        b = parser.parse(make_raw(manufacturer_data=NORMAL_DATA,
                                  mac_address="00:00:00:00:00:02"))
        assert a.identifier_hash == expected
        assert a.identifier_hash == b.identifier_hash

    def test_identity_hash_format(self, parser):
        result = parser.parse(make_raw(manufacturer_data=NORMAL_DATA))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestThermoBeaconMatching:
    def test_matches_lanyard_name(self, parser):
        assert parser.parse(make_raw(manufacturer_data=NORMAL_DATA,
                                     local_name="Lanyard")) is not None

    def test_matches_tp_name(self, parser):
        assert parser.parse(make_raw(manufacturer_data=NORMAL_DATA,
                                     local_name="TP358")) is not None

    def test_registry_matches_thermobeacon_name(self):
        from adwatch.registry import ParserRegistry, register_parser
        from adwatch.plugins.thermobeacon import THERMOBEACON_NAME_PATTERN

        registry = ParserRegistry()

        @register_parser(
            name="thermobeacon", company_id=THERMOBEACON_COMPANY_IDS,
            local_name_pattern=THERMOBEACON_NAME_PATTERN,
            description="ThermoBeacon", version="1.0.0", core=False,
            registry=registry,
        )
        class _P(ThermoBeaconParser):
            pass

        for name in ("ThermoBeacon", "TP357", "Lanyard"):
            assert len(registry.match(make_raw(local_name=name))) == 1, name
        assert registry.match(make_raw(local_name="Bose QC35")) == []


class TestThermoBeaconMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        assert parser.parse(make_raw(manufacturer_data=None, local_name="TP357")) is None

    def test_returns_none_too_short(self, parser):
        assert parser.parse(make_raw(manufacturer_data=b"\x10\x00" + bytes(4))) is None

    def test_returns_none_for_unknown_frame_length(self, parser):
        """Only the 18- and 20-byte frames have a documented layout."""
        assert parser.parse(make_raw(manufacturer_data=b"\x10\x00" + bytes(16))) is None

    def test_raw_payload_hex_excludes_company_id(self, parser):
        result = parser.parse(make_raw(manufacturer_data=NORMAL_DATA))
        assert result.raw_payload_hex == NORMAL_DATA[2:].hex()
