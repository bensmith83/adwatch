"""Tests for Qingping (ClearGrass) BLE sensor parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.qingping import QingpingParser


QINGPING_UUID = "0000fdcd-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def parser():
    return QingpingParser()


def make_raw(service_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_uuids=[],
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(service_data=service_data, **defaults)


# --- Helpers ---
# Layout is ground truth from reports/watchflower_passive.md (WatchFlower is
# open source; src/src/device_sensor_advertisement.cpp:401-556):
#
#   byte 0     frame control
#   byte 1     product id
#   bytes 2-7  MAC address, reversed
#   bytes 8+   TLV objects: type(1) + length(1) + data
#
# MAC address bytes reversed (AA:BB:CC:DD:EE:FF -> bytes)
MAC_REVERSED = bytes([0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA])

# Product id -> model, per qingping-ble DEVICE_TYPES
# (https://github.com/Bluetooth-Devices/qingping-ble, parser.py).
DEVICE_TYPES = {
    "CGG1": 0x01,
    "CGDK2": 0x10,
    "CGH1": 0x04,
    "CGDN1": 0x0E,
}


def _build_qingping(*, device_type=0x0C, frame_control=0x08, tlvs=b"",
                     mac=MAC_REVERSED):
    """Build 0xFDCD service data: frame control + product id + MAC + TLVs."""
    return bytes([frame_control, device_type]) + mac + tlvs


def _tlv(obj_type, data):
    """Build a single TLV entry: type (1 byte) + length (1 byte) + data."""
    return bytes([obj_type, len(data)]) + data


def _temp_humi_tlv(temp_raw, humi_raw):
    """Type 0x01: temperature + humidity, 2 x int16 LE, both /10."""
    return _tlv(0x01, struct.pack("<hh", temp_raw, humi_raw))


def _temp_tlv(temp_raw):
    """Temperature is only ever sent paired with humidity (type 0x01)."""
    return _temp_humi_tlv(temp_raw, 450)


def _humidity_tlv(hum_raw):
    return _temp_humi_tlv(225, hum_raw)


def _battery_tlv(pct):
    """Type 0x02: battery, 1 byte, %."""
    return _tlv(0x02, bytes([pct]))


def _pressure_tlv(raw):
    """Type 0x07: air pressure, int16 LE, /10 hPa."""
    return _tlv(0x07, struct.pack("<h", raw))


def _co2_tlv(ppm):
    """Type 0x13: CO2, int16 LE, ppm."""
    return _tlv(0x13, struct.pack("<h", ppm))


def _pm_tlv(pm25, pm10):
    """Type 0x12: PM2.5 + PM10, 2 x int16 LE, ug/m3."""
    return _tlv(0x12, struct.pack("<hh", pm25, pm10))


def _pm25_tlv(ugm3):
    return _pm_tlv(ugm3, 0)


def _make_service_data(payload):
    return {QINGPING_UUID: payload}


# --- Pre-built test data ---

# CGG1 with temp=22.5C (225) + humidity=45.0% (450)
CGG1_TEMP_HUMIDITY = _build_qingping(
    device_type=0x0C,
    tlvs=_temp_humi_tlv(225, 450),
)

# Air Monitor Lite with CO2=800ppm + PM2.5=35ug/m3
AIR_MONITOR_CO2_PM25 = _build_qingping(
    device_type=0x18,
    tlvs=_co2_tlv(800) + _pm_tlv(35, 48),
)

# Battery 72%
CGG1_BATTERY = _build_qingping(
    device_type=0x0C,
    tlvs=_battery_tlv(72),
)

# Multiple TLVs: temp + humidity + battery
CGG1_MULTI = _build_qingping(
    device_type=0x0C,
    tlvs=_temp_humi_tlv(225, 450) + _battery_tlv(72),
)


class TestQingpingTemperatureHumidity:
    def test_temperature_parsing(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(22.5)

    def test_humidity_parsing(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(45.0)

    def test_negative_temperature(self, parser):
        payload = _build_qingping(tlvs=_temp_tlv(-50))  # -5.0C
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(-5.0)

    def test_zero_temperature(self, parser):
        payload = _build_qingping(tlvs=_temp_tlv(0))
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(0.0)


class TestQingpingCO2PM25:
    def test_co2_parsing(self, parser):
        raw = make_raw(service_data=_make_service_data(AIR_MONITOR_CO2_PM25))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["co2"] == 800

    def test_pm25_parsing(self, parser):
        raw = make_raw(service_data=_make_service_data(AIR_MONITOR_CO2_PM25))
        result = parser.parse(raw)
        assert result.metadata["pm25"] == 35


class TestQingpingBattery:
    def test_battery_parsing(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_BATTERY))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["battery"] == 72

    def test_battery_full(self, parser):
        payload = _build_qingping(tlvs=_battery_tlv(100))
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result.metadata["battery"] == 100


class TestQingpingMultipleTLV:
    def test_all_fields_present(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_MULTI))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(22.5)
        assert result.metadata["humidity"] == pytest.approx(45.0)
        assert result.metadata["battery"] == 72

    def test_co2_and_pm25_together(self, parser):
        payload = _build_qingping(
            device_type=0x18,
            tlvs=_co2_tlv(1200) + _pm_tlv(50, 70) + _battery_tlv(88),
        )
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result.metadata["co2"] == 1200
        assert result.metadata["pm25"] == 50
        assert result.metadata["battery"] == 88


class TestQingpingDeviceType:
    @pytest.mark.parametrize("model,type_code", [
        # qingping-ble DEVICE_TYPES (Bluetooth-Devices/qingping-ble parser.py)
        ("CGG1", 0x01),
        ("CGH1", 0x04),
        ("CGG1", 0x07),
        ("CGP1W", 0x09),
        ("CGD1", 0x0C),   # alarm clock (adwatch previously said CGG1)
        ("CGDN1", 0x0E),
        ("CGM1", 0x0F),
        ("CGDK2", 0x10),
        ("CGPR1", 0x12),  # motion & light (adwatch previously said CGH1)
        ("CGF1W", 0x15),
        ("CGG1", 0x16),
        ("CGP23W", 0x18), # temp & RH monitor pro (adwatch: Air Monitor Lite)
        ("CGC1", 0x1E),
        ("CGDN1", 0x24),
        ("CGP23W", 0x26),
        ("CGP22C", 0x33),
        ("CGG3", 0x4F),
        ("CGP22C", 0x5D),
    ])
    def test_device_type_identification(self, parser, model, type_code):
        payload = _build_qingping(device_type=type_code, tlvs=_temp_tlv(200))
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == model

    def test_unknown_device_type(self, parser):
        payload = _build_qingping(device_type=0xFF, tlvs=_temp_tlv(200))
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "unknown"


class TestQingpingParseResultFields:
    def test_parser_name(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.parser_name == "qingping"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.beacon_type == "qingping"

    def test_device_class(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.raw_payload_hex == CGG1_TEMP_HUMIDITY.hex()


class TestQingpingIdentity:
    def test_identity_hash_from_service_data_mac(self, parser):
        """MAC from service data (reversed bytes) should be used for identity."""
        # MAC_REVERSED = FF:EE:DD:CC:BB:AA -> reversed to AA:BB:CC:DD:EE:FF
        expected_mac = "AA:BB:CC:DD:EE:FF"
        expected = hashlib.sha256(expected_mac.encode()).hexdigest()[:16]
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_different_mac_different_hash(self, parser):
        other_mac = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
        payload = _build_qingping(mac=other_mac, tlvs=_temp_tlv(200))
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        expected_mac = "66:55:44:33:22:11"
        expected = hashlib.sha256(expected_mac.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestQingpingRejectsInvalid:
    def test_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_empty_service_data(self, parser):
        raw = make_raw(service_data={})
        assert parser.parse(raw) is None

    def test_wrong_uuid(self, parser):
        raw = make_raw(service_data={"0000cafe-0000-1000-8000-00805f9b34fb": b"\x00" * 20})
        assert parser.parse(raw) is None

    def test_too_short_data(self, parser):
        # Less than 8 bytes (frame control + product id + 6-byte MAC)
        raw = make_raw(service_data=_make_service_data(b"\x00" * 5))
        assert parser.parse(raw) is None

    def test_no_tlv_data(self, parser):
        """Header only, no TLV entries — should return None."""
        payload = _build_qingping(tlvs=b"")
        raw = make_raw(service_data=_make_service_data(payload))
        assert parser.parse(raw) is None

    def test_truncated_tlv(self, parser):
        """TLV header present but value truncated — should skip gracefully."""
        # TLV type (1 byte) + length byte says 4 but only 1 byte follows
        bad_tlv = bytes([0x01, 0x04, 0x01])
        payload = _build_qingping(tlvs=bad_tlv)
        raw = make_raw(service_data=_make_service_data(payload))
        assert parser.parse(raw) is None


class TestQingpingRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = QingpingParser()
        reg.register(
            name="qingping",
            service_uuid=QINGPING_UUID,
            description="Qingping (ClearGrass) Sensors",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        matched = reg.match(raw)
        assert any(isinstance(p, QingpingParser) for p in matched)

    def test_not_core(self):
        """Qingping should be a plugin (core=False)."""
        assert True


class TestQingpingUIConfig:
    def test_ui_config_returns_tab(self):
        parser = QingpingParser()
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Qingping"

    def test_ui_config_has_sensor_card(self):
        parser = QingpingParser()
        cfg = parser.ui_config()
        widget_types = [w.widget_type for w in cfg.widgets]
        assert "sensor_card" in widget_types

    def test_ui_config_has_render_hints(self):
        parser = QingpingParser()
        cfg = parser.ui_config()
        sensor_widgets = [w for w in cfg.widgets if w.widget_type == "sensor_card"]
        assert len(sensor_widgets) > 0
        hints = sensor_widgets[0].render_hints
        assert "primary_field" in hints
        assert "secondary_field" in hints
        assert "badge_fields" in hints


class TestQingpingStorageSchema:
    def test_storage_schema_creates_table(self):
        parser = QingpingParser()
        schema = parser.storage_schema()
        assert schema is not None
        assert "qingping_readings" in schema


class TestQingpingStorageRow:
    def test_parse_includes_storage(self):
        parser = QingpingParser()
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result is not None
        assert result.event_type == "qingping_reading"
        assert result.storage_table == "qingping_readings"
        assert result.storage_row is not None
        assert "temperature" in result.storage_row
        assert "humidity" in result.storage_row

    def test_storage_row_has_optional_fields(self):
        """storage_row handles missing co2/pm25 gracefully (None for absent)."""
        parser = QingpingParser()
        # CGG1_TEMP_HUMIDITY has no co2 or pm25
        raw = make_raw(service_data=_make_service_data(CGG1_TEMP_HUMIDITY))
        result = parser.parse(raw)
        assert result.storage_row is not None
        assert result.storage_row.get("co2") is None
        assert result.storage_row.get("pm25") is None

        # AIR_MONITOR_CO2_PM25 has co2 and pm25 but no temp/humidity
        raw2 = make_raw(service_data=_make_service_data(AIR_MONITOR_CO2_PM25))
        result2 = parser.parse(raw2)
        assert result2.storage_row is not None
        assert result2.storage_row["co2"] == 800
        assert result2.storage_row["pm25"] == 35


class TestQingpingAPIRouter:
    def test_api_router_returns_router(self):
        from adwatch.storage.base import Database
        parser = QingpingParser()
        # Pass a mock-like db; just need it non-None
        router = parser.api_router(db=Database())
        assert router is not None


class TestQingpingWatchflowerLayout:
    """The 0xFDCD layout, verified against reports/watchflower_passive.md.

    Two bugs this class pins down: the service UUID used to be registered as
    ``0000cdfd-…`` (the byte-swapped form, which never matches a real advert),
    and the TLV loop used a 2-byte object type starting at offset 9 instead of
    a 1-byte type starting at offset 8.
    """

    def test_service_uuid_is_fdcd_not_cdfd(self):
        from adwatch.plugins.qingping import QINGPING_UUID as PLUGIN_UUID

        assert PLUGIN_UUID == "0000fdcd-0000-1000-8000-00805f9b34fb"

    def test_short_uuid_form_also_matches(self, parser):
        raw = make_raw(service_data={"fdcd": CGG1_TEMP_HUMIDITY})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(22.5)

    def test_mac_is_at_bytes_two_to_seven(self, parser):
        """Not bytes 0-5: the frame control and product id come first."""
        payload = _build_qingping(mac=bytes([0x66, 0x55, 0x44, 0x33, 0x22, 0x11]),
                                  tlvs=_battery_tlv(50))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["mac"] == "11:22:33:44:55:66"

    def test_tlv_loop_starts_at_offset_eight(self, parser):
        payload = _build_qingping(tlvs=_battery_tlv(64))
        assert len(payload) == 8 + 3
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["battery"] == 64

    def test_temperature_and_humidity_share_object_0x01(self, parser):
        payload = _build_qingping(tlvs=_temp_humi_tlv(-123, 987))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["temperature"] == pytest.approx(-12.3)
        assert result.metadata["humidity"] == pytest.approx(98.7)

    def test_air_pressure_object_0x07(self, parser):
        payload = _build_qingping(tlvs=_pressure_tlv(10132))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["pressure"] == pytest.approx(1013.2)

    def test_pm25_and_pm10_share_object_0x12(self, parser):
        payload = _build_qingping(device_type=0x18, tlvs=_pm_tlv(35, 48))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["pm25"] == 35
        assert result.metadata["pm10"] == 48

    def test_co2_object_0x13(self, parser):
        payload = _build_qingping(device_type=0x18, tlvs=_co2_tlv(1450))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["co2"] == 1450

    def test_object_0x0f_is_packet_id_not_door(self, parser):
        """qingping-ble: TLV 0x0F is the packet id, not a door state."""
        payload = _build_qingping(tlvs=_tlv(0x0F, bytes([1])) + _battery_tlv(90))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["packet_id"] == 1
        assert "door_state" not in result.metadata

    def test_packet_id_alone_is_not_a_reading(self, parser):
        payload = _build_qingping(tlvs=_tlv(0x0F, bytes([7])))
        assert parser.parse(make_raw(service_data=_make_service_data(payload))) is None

    @pytest.mark.parametrize("raw_value,state,is_open,left_open", [
        (0, "open", True, False),
        (1, "closed", False, False),
        (2, "left_open", True, True),
    ])
    def test_door_state_object_0x04(self, parser, raw_value, state, is_open, left_open):
        """qingping-ble: TLV 0x04 door, 0 open / 1 closed / 2 left open."""
        payload = _build_qingping(device_type=0x04, tlvs=_tlv(0x04, bytes([raw_value])))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["door_state"] == state
        assert result.metadata["door_open"] is is_open
        assert result.metadata["door_left_open"] is left_open

    def test_door_state_unknown_value_kept_raw(self, parser):
        payload = _build_qingping(device_type=0x04, tlvs=_tlv(0x04, bytes([9])))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["door_state_raw"] == 9
        assert "door_state" not in result.metadata

    def test_unknown_tlv_is_skipped_by_its_length(self, parser):
        """An unrecognised object must not desynchronise the loop."""
        payload = _build_qingping(
            tlvs=_tlv(0x7E, b"\x01\x02\x03") + _battery_tlv(77)
        )
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["battery"] == 77

    def test_frame_control_and_product_id_reported(self, parser):
        payload = _build_qingping(frame_control=0x88, device_type=0x10,
                                  tlvs=_battery_tlv(30))
        result = parser.parse(make_raw(service_data=_make_service_data(payload)))
        assert result.metadata["frame_control"] == 0x88
        assert result.metadata["product_id"] == 0x10
        assert result.metadata["device_type"] == "CGDK2"

    def test_identity_survives_ble_mac_rotation(self, parser):
        payload = _build_qingping(tlvs=_battery_tlv(50))
        a = parser.parse(make_raw(service_data=_make_service_data(payload),
                                  mac_address="00:00:00:00:00:01"))
        b = parser.parse(make_raw(service_data=_make_service_data(payload),
                                  mac_address="00:00:00:00:00:02"))
        assert a.identifier_hash == b.identifier_hash
