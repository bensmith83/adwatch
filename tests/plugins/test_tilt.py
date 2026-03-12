"""Tests for Tilt Hydrometer BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.plugins.tilt import TiltParser


@pytest.fixture
def parser():
    return TiltParser()


def make_raw(manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# --- iBeacon Tilt builder ---

APPLE_COMPANY_ID = bytes([0x4C, 0x00])  # 0x004C little-endian
IBEACON_PREFIX = bytes([0x02, 0x15])  # subtype + length

TILT_UUIDS = {
    "red":    "A495BB10-C5B1-4B44-B512-1370F02D74DE",
    "green":  "A495BB20-C5B1-4B44-B512-1370F02D74DE",
    "black":  "A495BB30-C5B1-4B44-B512-1370F02D74DE",
    "purple": "A495BB40-C5B1-4B44-B512-1370F02D74DE",
    "orange": "A495BB50-C5B1-4B44-B512-1370F02D74DE",
    "blue":   "A495BB60-C5B1-4B44-B512-1370F02D74DE",
    "yellow": "A495BB70-C5B1-4B44-B512-1370F02D74DE",
    "pink":   "A495BB80-C5B1-4B44-B512-1370F02D74DE",
}


def uuid_to_bytes(uuid_str):
    return bytes.fromhex(uuid_str.replace("-", ""))


def _build_tilt(*, color="red", temp_f=72, gravity_x1000=1050, tx_power=-59):
    uuid_bytes = uuid_to_bytes(TILT_UUIDS[color])
    major = struct.pack(">H", temp_f)
    minor = struct.pack(">H", gravity_x1000)
    return APPLE_COMPANY_ID + IBEACON_PREFIX + uuid_bytes + major + minor + bytes([tx_power & 0xFF])


# --- Pre-built test data ---

TILT_RED_72F_1050 = _build_tilt(color="red", temp_f=72, gravity_x1000=1050)
TILT_GREEN_68F_1045 = _build_tilt(color="green", temp_f=68, gravity_x1000=1045)
TILT_BLACK_32F_1000 = _build_tilt(color="black", temp_f=32, gravity_x1000=1000)

NON_TILT_IBEACON = (
    APPLE_COMPANY_ID + IBEACON_PREFIX
    + bytes(16)  # non-Tilt UUID
    + struct.pack(">HH", 100, 200) + bytes([0xC5])
)


class TestTiltColorDetection:
    @pytest.mark.parametrize("color", list(TILT_UUIDS.keys()))
    def test_detects_color(self, parser, color):
        data = _build_tilt(color=color)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["color"] == color


class TestTiltTemperature:
    def test_temperature_fahrenheit(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.metadata["temperature_f"] == 72

    def test_temperature_celsius_conversion(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        expected_c = round((72 - 32) * 5 / 9, 1)
        assert result.metadata["temperature_c"] == expected_c

    def test_freezing_point(self, parser):
        data = _build_tilt(temp_f=32)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["temperature_f"] == 32
        assert result.metadata["temperature_c"] == 0.0

    def test_boiling_point(self, parser):
        data = _build_tilt(temp_f=212)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["temperature_f"] == 212
        assert result.metadata["temperature_c"] == 100.0


class TestTiltSpecificGravity:
    def test_typical_gravity(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.metadata["specific_gravity"] == 1.050

    def test_water_gravity(self, parser):
        data = _build_tilt(gravity_x1000=1000)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["specific_gravity"] == 1.000

    def test_high_gravity(self, parser):
        data = _build_tilt(gravity_x1000=1120)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["specific_gravity"] == 1.120


class TestTiltFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.parser_name == "tilt"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.beacon_type == "tilt"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        expected = TILT_RED_72F_1050[2:].hex()
        assert result.raw_payload_hex == expected

    def test_metadata_has_uuid(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.metadata["uuid"] == TILT_UUIDS["red"]


class TestTiltIdentity:
    def test_identity_hash_from_uuid(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        expected = hashlib.sha256(TILT_UUIDS["red"].encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_different_colors_different_hashes(self, parser):
        red_raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        green_raw = make_raw(manufacturer_data=TILT_GREEN_68F_1045)
        red_result = parser.parse(red_raw)
        green_result = parser.parse(green_raw)
        assert red_result.identifier_hash != green_result.identifier_hash


class TestTiltRejectsInvalid:
    def test_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_empty_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=b"")
        assert parser.parse(raw) is None

    def test_wrong_company_id(self, parser):
        data = bytes([0xDC, 0x00]) + b"\x02\x15" + bytes(21)
        raw = make_raw(manufacturer_data=data)
        assert parser.parse(raw) is None

    def test_wrong_ibeacon_subtype(self, parser):
        uuid_bytes = uuid_to_bytes(TILT_UUIDS["red"])
        data = APPLE_COMPANY_ID + bytes([0x03, 0x15]) + uuid_bytes + struct.pack(">HH", 72, 1050) + bytes([0xC5])
        raw = make_raw(manufacturer_data=data)
        assert parser.parse(raw) is None

    def test_non_tilt_uuid(self, parser):
        raw = make_raw(manufacturer_data=NON_TILT_IBEACON)
        assert parser.parse(raw) is None

    def test_too_short(self, parser):
        raw = make_raw(manufacturer_data=APPLE_COMPANY_ID + IBEACON_PREFIX + bytes(10))
        assert parser.parse(raw) is None


class TestTiltRegistration:
    def test_registered_with_company_id(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = TiltParser()
        reg.register(
            name="tilt",
            company_id=0x004C,
            description="Tilt Hydrometer",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        matched = reg.match(raw)
        assert any(isinstance(p, TiltParser) for p in matched)


class TestTiltUIConfig:
    def test_ui_config_returns_tab(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert isinstance(cfg, PluginUIConfig)
        assert cfg.tab_name == "Tilt"

    def test_ui_config_has_sensor_card(self, parser):
        cfg = parser.ui_config()
        widget_types = [w.widget_type for w in cfg.widgets]
        assert "sensor_card" in widget_types

    def test_ui_config_has_render_hints(self, parser):
        cfg = parser.ui_config()
        sensor_widgets = [w for w in cfg.widgets if w.widget_type == "sensor_card"]
        assert len(sensor_widgets) > 0
        hints = sensor_widgets[0].render_hints
        assert "primary_field" in hints
        assert "secondary_field" in hints
        assert "badge_fields" in hints


class TestTiltStorageSchema:
    def test_storage_schema_creates_table(self, parser):
        schema = parser.storage_schema()
        assert schema is not None
        assert "tilt_readings" in schema
        assert "CREATE TABLE" in schema


class TestTiltStorageIntegration:
    def test_parse_includes_storage_table(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.storage_table == "tilt_readings"

    def test_parse_includes_event_type(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050)
        result = parser.parse(raw)
        assert result.event_type == "tilt_reading"

    def test_parse_includes_storage_row(self, parser):
        raw = make_raw(manufacturer_data=TILT_RED_72F_1050, rssi=-65)
        result = parser.parse(raw)
        row = result.storage_row
        assert row is not None
        assert "timestamp" in row
        assert "mac_address" in row
        assert "color" in row
        assert "temperature_f" in row
        assert "temperature_c" in row
        assert "specific_gravity" in row
        assert "uuid" in row
        assert "identifier_hash" in row
        assert "rssi" in row
        assert "raw_payload_hex" in row
        assert row["color"] == "red"
        assert row["temperature_f"] == 72
        assert row["rssi"] == -65


class TestTiltAPIRouter:
    def test_api_router_returns_router(self, parser):
        from unittest.mock import MagicMock
        db = MagicMock()
        router = parser.api_router(db)
        from fastapi import APIRouter
        assert isinstance(router, APIRouter)
