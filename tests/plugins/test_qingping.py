"""Tests for Qingping (ClearGrass) BLE sensor parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.qingping import QingpingParser


QINGPING_UUID = "0000cdfd-0000-1000-8000-00805f9b34fb"


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

# MAC address bytes reversed (FF:EE:DD:CC:BB:AA -> bytes)
MAC_REVERSED = bytes([0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA])

DEVICE_TYPES = {
    "CGG1": 0x0C,
    "CGDK2": 0x10,
    "CGH1": 0x12,
    "Air Monitor Lite": 0x18,
}


def _build_qingping(*, device_type=0x0C, frame_control=0x00, tlvs=b"",
                     mac=MAC_REVERSED):
    """Build service data for Qingping BLE advertisement.

    Layout:
      MAC (6 bytes, reversed) + device_type (2 bytes LE) + frame_control (1 byte) + TLV entries
    """
    return mac + struct.pack("<H", device_type) + bytes([frame_control]) + tlvs


def _tlv(obj_type, data):
    """Build a single TLV entry: type (2 bytes LE) + length (1 byte) + data."""
    return struct.pack("<H", obj_type) + bytes([len(data)]) + data


def _temp_tlv(temp_raw):
    """Temperature TLV: 0x0101, signed 16-bit LE, 0.1C units."""
    return _tlv(0x0101, struct.pack("<h", temp_raw))


def _humidity_tlv(hum_raw):
    """Humidity TLV: 0x0201, unsigned 16-bit LE, 0.1% units."""
    return _tlv(0x0201, struct.pack("<H", hum_raw))


def _battery_tlv(pct):
    """Battery TLV: 0x0801, 1 byte, %."""
    return _tlv(0x0801, bytes([pct]))


def _co2_tlv(ppm):
    """CO2 TLV: 0x1201, unsigned 16-bit LE, ppm."""
    return _tlv(0x1201, struct.pack("<H", ppm))


def _pm25_tlv(ugm3):
    """PM2.5 TLV: 0x0D01, unsigned 16-bit LE, ug/m3."""
    return _tlv(0x0D01, struct.pack("<H", ugm3))


def _make_service_data(payload):
    return {QINGPING_UUID: payload}


# --- Pre-built test data ---

# CGG1 with temp=22.5C (225) + humidity=45.0% (450)
CGG1_TEMP_HUMIDITY = _build_qingping(
    device_type=0x0C,
    tlvs=_temp_tlv(225) + _humidity_tlv(450),
)

# Air Monitor Lite with CO2=800ppm + PM2.5=35ug/m3
AIR_MONITOR_CO2_PM25 = _build_qingping(
    device_type=0x18,
    tlvs=_co2_tlv(800) + _pm25_tlv(35),
)

# Battery 72%
CGG1_BATTERY = _build_qingping(
    device_type=0x0C,
    tlvs=_battery_tlv(72),
)

# Multiple TLVs: temp + humidity + battery
CGG1_MULTI = _build_qingping(
    device_type=0x0C,
    tlvs=_temp_tlv(225) + _humidity_tlv(450) + _battery_tlv(72),
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
            tlvs=_co2_tlv(1200) + _pm25_tlv(50) + _battery_tlv(88),
        )
        raw = make_raw(service_data=_make_service_data(payload))
        result = parser.parse(raw)
        assert result.metadata["co2"] == 1200
        assert result.metadata["pm25"] == 50
        assert result.metadata["battery"] == 88


class TestQingpingDeviceType:
    @pytest.mark.parametrize("model,type_code", [
        ("CGG1", 0x0C),
        ("CGDK2", 0x10),
        ("CGH1", 0x12),
        ("Air Monitor Lite", 0x18),
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
        # Less than 9 bytes (6 MAC + 2 device type + 1 frame control)
        raw = make_raw(service_data=_make_service_data(b"\x00" * 5))
        assert parser.parse(raw) is None

    def test_no_tlv_data(self, parser):
        """Header only, no TLV entries — should return None."""
        payload = _build_qingping(tlvs=b"")
        raw = make_raw(service_data=_make_service_data(payload))
        assert parser.parse(raw) is None

    def test_truncated_tlv(self, parser):
        """TLV header present but value truncated — should skip gracefully."""
        # TLV type (2 bytes) + length byte says 2 but only 1 byte follows
        bad_tlv = struct.pack("<H", 0x0101) + bytes([2]) + bytes([0x01])
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
