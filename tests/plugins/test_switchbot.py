"""Tests for SwitchBot BLE parser plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.switchbot import SwitchBotParser


SWITCHBOT_UUID = "0000fd3d-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def parser():
    return SwitchBotParser()


def make_raw(service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data, local_name=local_name, **defaults
    )


def _sd(payload: bytes) -> dict[str, bytes]:
    """Wrap payload as SwitchBot service data dict."""
    return {SWITCHBOT_UUID: payload}


# --- Meter (device type 0x54 = 'T') ---

def _build_meter(*, temp_int=25, temp_sign=0, temp_dec=8, humidity=60, battery=85):
    """Build service data for Meter.

    Byte 0: 0x54 (device type)
    Byte 1: bit7=temp_sign, bits6-0=temp integer
    Byte 2: bits3-0=temp decimal (tenths), bit7=humidity alert, bit6=temp alert
    Byte 3: humidity percent
    Byte 4: battery percent
    """
    b0 = 0x54
    b1 = (temp_sign << 7) | (temp_int & 0x7F)
    b2 = temp_dec & 0x0F
    return bytes([b0, b1, b2, humidity, battery])


METER_VALID = _build_meter()
METER_NEG_TEMP = _build_meter(temp_sign=1, temp_int=5, temp_dec=3)
METER_ZERO_TEMP = _build_meter(temp_int=0, temp_dec=0, humidity=50, battery=100)


# --- Bot (device type 0x48 = 'H') ---

def _build_bot(*, mode=0, state=0, battery=90):
    """Build service data for Bot.

    Byte 0: 0x48 (device type)
    Byte 1: bit7=mode (0=press, 1=switch), bit6=state (0=off, 1=on)
    Byte 2: battery percent
    """
    b0 = 0x48
    b1 = (mode << 7) | (state << 6)
    return bytes([b0, b1, battery])


BOT_PRESS_OFF = _build_bot(mode=0, state=0, battery=90)
BOT_SWITCH_ON = _build_bot(mode=1, state=1, battery=75)
BOT_SWITCH_OFF = _build_bot(mode=1, state=0, battery=50)


# --- Curtain (device type 0x63 = 'c') ---

def _build_curtain(*, calibrated=1, position=50, moving=0, direction=0, battery=80):
    """Build service data for Curtain.

    Byte 0: 0x63 (device type)
    Byte 1: bit7=calibration done, bits6-0=position (0-100)
    Byte 2: bit7=moving, bit6=direction (0=opening, 1=closing)
    Byte 3: battery (0xFF = not available)
    """
    b0 = 0x63
    b1 = (calibrated << 7) | (position & 0x7F)
    b2 = (moving << 7) | (direction << 6)
    return bytes([b0, b1, b2, battery])


CURTAIN_OPEN = _build_curtain(position=0, calibrated=1, battery=80)
CURTAIN_CLOSED = _build_curtain(position=100, calibrated=1, battery=60)
CURTAIN_MOVING = _build_curtain(position=50, moving=1, direction=1, battery=70)
CURTAIN_NO_BATTERY = _build_curtain(position=25, battery=0xFF)


# --- Contact Sensor (device type 0x64 = 'd') ---

def _build_contact(*, contact_open=0, motion=0, battery=95):
    """Build service data for Contact Sensor.

    Byte 0: 0x64 (device type)
    Byte 1: bit1=contact state (0=closed, 1=open), bit0=motion detected
    Byte 2: battery percent
    """
    b0 = 0x64
    b1 = (contact_open << 1) | motion
    return bytes([b0, b1, battery])


CONTACT_CLOSED_NO_MOTION = _build_contact(contact_open=0, motion=0, battery=95)
CONTACT_OPEN_WITH_MOTION = _build_contact(contact_open=1, motion=1, battery=80)


# --- Motion Sensor (device type 0x73 = 's') ---

def _build_motion(*, motion_detected=0, led_enabled=0, battery=88):
    """Build service data for Motion Sensor.

    Byte 0: 0x73 (device type)
    Byte 1: bit0=motion detected, bit1=LED enabled
    Byte 2: battery percent
    """
    b0 = 0x73
    b1 = (led_enabled << 1) | motion_detected
    return bytes([b0, b1, battery])


MOTION_DETECTED = _build_motion(motion_detected=1, led_enabled=0, battery=88)
MOTION_IDLE = _build_motion(motion_detected=0, led_enabled=1, battery=92)


# --- Plug Mini (device type 0x6A = 'j') ---

def _build_plug_mini(*, power=0, watts=0, overload=0):
    b0 = 0x6A
    b1 = (power << 7)
    b2 = watts & 0xFF
    b3 = overload & 1
    return bytes([b0, b1, b2, b3])


PLUG_ON_50W = _build_plug_mini(power=1, watts=50, overload=0)
PLUG_OFF_0W = _build_plug_mini(power=0, watts=0, overload=0)
PLUG_OVERLOAD = _build_plug_mini(power=1, watts=200, overload=1)


# --- Lock (device type 0x6F = 'o') ---

def _build_lock(*, lock_state=0, door_state=0, battery=80, reserved=0):
    b0 = 0x6F
    b1 = (lock_state << 6) | (door_state << 5)
    b2 = battery
    b3 = reserved
    return bytes([b0, b1, b2, b3])


LOCK_LOCKED_CLOSED = _build_lock(lock_state=0, door_state=0, battery=80)
LOCK_UNLOCKED_OPEN = _build_lock(lock_state=1, door_state=1, battery=60)
LOCK_JAMMED = _build_lock(lock_state=2, door_state=0, battery=50)


# --- Humidifier (device type 0x65 = 'e') ---

def _build_humidifier(*, power=0, mode=0, humidity_setting=50, water_low=0):
    b0 = 0x65
    b1 = (power << 7) | ((mode & 0x07) << 4)
    b2 = humidity_setting
    b3 = (water_low << 7)
    return bytes([b0, b1, b2, b3])


HUMIDIFIER_ON_AUTO = _build_humidifier(power=1, mode=0, humidity_setting=55, water_low=0)
HUMIDIFIER_OFF = _build_humidifier(power=0, mode=1, humidity_setting=40, water_low=0)
HUMIDIFIER_WATER_LOW = _build_humidifier(power=1, mode=3, humidity_setting=70, water_low=1)


# --- Color Bulb (device type 0x75 = 'u') ---

def _build_color_bulb(*, power=0, brightness=50, color_mode=0):
    b0 = 0x75
    b1 = (power << 7) | (brightness & 0x7F)
    b2 = (color_mode << 6)
    return bytes([b0, b1, b2])


BULB_ON_WHITE = _build_color_bulb(power=1, brightness=80, color_mode=0)
BULB_ON_COLOR = _build_color_bulb(power=1, brightness=50, color_mode=1)
BULB_ON_SCENE = _build_color_bulb(power=1, brightness=100, color_mode=2)
BULB_OFF = _build_color_bulb(power=0, brightness=0, color_mode=0)


# --- Blind Tilt (device type 0x3C = '<') ---

def _build_blind_tilt(*, calibrated=1, position=50, direction=0, reserved=0):
    b0 = 0x3C
    b1 = (calibrated << 7) | (position & 0x7F)
    b2 = (direction << 6)
    b3 = reserved
    return bytes([b0, b1, b2, b3])


BLIND_OPEN = _build_blind_tilt(position=0, calibrated=1, direction=0)
BLIND_CLOSED = _build_blind_tilt(position=100, calibrated=1, direction=1)
BLIND_UNCALIBRATED = _build_blind_tilt(position=50, calibrated=0, direction=0)


# --- Hub 2 (device type 0x77 = 'w') ---

def _build_hub2(*, temp_sign=0, temp_int=22, temp_dec=5, humidity=55, light_level=10):
    b0 = 0x77
    b1 = (temp_sign << 7) | (temp_int & 0x7F)
    b2 = temp_dec & 0x0F
    b3 = humidity
    b4 = light_level
    return bytes([b0, b1, b2, b3, b4])


HUB2_NORMAL = _build_hub2(temp_int=22, temp_dec=5, humidity=55, light_level=10)
HUB2_NEG_TEMP = _build_hub2(temp_sign=1, temp_int=3, temp_dec=2, humidity=80, light_level=0)
HUB2_BRIGHT = _build_hub2(temp_int=30, temp_dec=0, humidity=40, light_level=20)


# --- Outdoor Meter (device type 0x69 = 'i') ---

def _build_outdoor_meter(*, temp_sign=0, temp_int=18, temp_dec=6, humidity=65, battery=90):
    b0 = 0x69
    b1 = (temp_sign << 7) | (temp_int & 0x7F)
    b2 = temp_dec & 0x0F
    b3 = humidity
    b4 = battery
    return bytes([b0, b1, b2, b3, b4])


OUTDOOR_NORMAL = _build_outdoor_meter(temp_int=18, temp_dec=6, humidity=65, battery=90)
OUTDOOR_NEG = _build_outdoor_meter(temp_sign=1, temp_int=10, temp_dec=1, humidity=90, battery=70)


# ======================================================================
# Test classes
# ======================================================================


class TestMeterTemperature:
    def test_positive_temperature(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result is not None
        # temp_int=25, temp_dec=8 -> 25.8
        assert result.metadata["temperature_c"] == pytest.approx(25.8)

    def test_negative_temperature(self, parser):
        raw = make_raw(service_data=_sd(METER_NEG_TEMP))
        result = parser.parse(raw)
        assert result is not None
        # sign=1, int=5, dec=3 -> -5.3
        assert result.metadata["temperature_c"] == pytest.approx(-5.3)

    def test_zero_temperature(self, parser):
        raw = make_raw(service_data=_sd(METER_ZERO_TEMP))
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(0.0)

    def test_decimal_precision(self, parser):
        data = _build_meter(temp_int=20, temp_dec=5)
        raw = make_raw(service_data=_sd(data))
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(20.5)


class TestMeterHumidity:
    def test_humidity_value(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == 60

    def test_zero_humidity(self, parser):
        data = _build_meter(humidity=0)
        raw = make_raw(service_data=_sd(data))
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == 0

    def test_max_humidity(self, parser):
        data = _build_meter(humidity=100)
        raw = make_raw(service_data=_sd(data))
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == 100


class TestMeterBattery:
    def test_battery_value(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 85


class TestBotMode:
    def test_press_mode(self, parser):
        raw = make_raw(service_data=_sd(BOT_PRESS_OFF))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["mode"] == "press"

    def test_switch_mode(self, parser):
        raw = make_raw(service_data=_sd(BOT_SWITCH_ON))
        result = parser.parse(raw)
        assert result.metadata["mode"] == "switch"


class TestBotState:
    def test_state_off(self, parser):
        raw = make_raw(service_data=_sd(BOT_PRESS_OFF))
        result = parser.parse(raw)
        assert result.metadata["state"] == "off"

    def test_state_on(self, parser):
        raw = make_raw(service_data=_sd(BOT_SWITCH_ON))
        result = parser.parse(raw)
        assert result.metadata["state"] == "on"

    def test_switch_mode_off(self, parser):
        raw = make_raw(service_data=_sd(BOT_SWITCH_OFF))
        result = parser.parse(raw)
        assert result.metadata["mode"] == "switch"
        assert result.metadata["state"] == "off"


class TestBotBattery:
    def test_battery_value(self, parser):
        raw = make_raw(service_data=_sd(BOT_PRESS_OFF))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 90


class TestCurtainPosition:
    def test_fully_open(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_OPEN))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["position"] == 0

    def test_fully_closed(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_CLOSED))
        result = parser.parse(raw)
        assert result.metadata["position"] == 100

    def test_half_open(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_MOVING))
        result = parser.parse(raw)
        assert result.metadata["position"] == 50


class TestCurtainCalibration:
    def test_calibrated(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_OPEN))
        result = parser.parse(raw)
        assert result.metadata["calibrated"] is True

    def test_not_calibrated(self, parser):
        data = _build_curtain(calibrated=0, position=30)
        raw = make_raw(service_data=_sd(data))
        result = parser.parse(raw)
        assert result.metadata["calibrated"] is False


class TestCurtainMoving:
    def test_moving_closing(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_MOVING))
        result = parser.parse(raw)
        assert result.metadata["moving"] is True
        assert result.metadata["direction"] == "closing"

    def test_not_moving(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_OPEN))
        result = parser.parse(raw)
        assert result.metadata["moving"] is False

    def test_moving_opening(self, parser):
        data = _build_curtain(moving=1, direction=0, position=60)
        raw = make_raw(service_data=_sd(data))
        result = parser.parse(raw)
        assert result.metadata["moving"] is True
        assert result.metadata["direction"] == "opening"


class TestCurtainBattery:
    def test_battery_value(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_OPEN))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 80

    def test_battery_not_available(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_NO_BATTERY))
        result = parser.parse(raw)
        assert result.metadata.get("battery_percent") is None


class TestContactSensor:
    def test_contact_closed(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_CLOSED_NO_MOTION))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["contact"] == "closed"

    def test_contact_open(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_OPEN_WITH_MOTION))
        result = parser.parse(raw)
        assert result.metadata["contact"] == "open"

    def test_motion_detected(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_OPEN_WITH_MOTION))
        result = parser.parse(raw)
        assert result.metadata["motion"] is True

    def test_no_motion(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_CLOSED_NO_MOTION))
        result = parser.parse(raw)
        assert result.metadata["motion"] is False

    def test_battery(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_CLOSED_NO_MOTION))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 95


class TestMotionSensor:
    def test_motion_detected(self, parser):
        raw = make_raw(service_data=_sd(MOTION_DETECTED))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["motion"] is True

    def test_no_motion(self, parser):
        raw = make_raw(service_data=_sd(MOTION_IDLE))
        result = parser.parse(raw)
        assert result.metadata["motion"] is False

    def test_led_enabled(self, parser):
        raw = make_raw(service_data=_sd(MOTION_IDLE))
        result = parser.parse(raw)
        assert result.metadata["led_enabled"] is True

    def test_led_disabled(self, parser):
        raw = make_raw(service_data=_sd(MOTION_DETECTED))
        result = parser.parse(raw)
        assert result.metadata["led_enabled"] is False

    def test_battery(self, parser):
        raw = make_raw(service_data=_sd(MOTION_DETECTED))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 88


class TestPlugMini:
    def test_power_on(self, parser):
        raw = make_raw(service_data=_sd(PLUG_ON_50W))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["power_state"] == "on"

    def test_power_off(self, parser):
        raw = make_raw(service_data=_sd(PLUG_OFF_0W))
        result = parser.parse(raw)
        assert result.metadata["power_state"] == "off"

    def test_watts(self, parser):
        raw = make_raw(service_data=_sd(PLUG_ON_50W))
        result = parser.parse(raw)
        assert result.metadata["watts"] == 50

    def test_overload_true(self, parser):
        raw = make_raw(service_data=_sd(PLUG_OVERLOAD))
        result = parser.parse(raw)
        assert result.metadata["overload"] is True

    def test_overload_false(self, parser):
        raw = make_raw(service_data=_sd(PLUG_ON_50W))
        result = parser.parse(raw)
        assert result.metadata["overload"] is False

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(PLUG_ON_50W))
        result = parser.parse(raw)
        assert result.device_class == "switch"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(PLUG_ON_50W))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "plug_mini"


class TestLock:
    def test_locked(self, parser):
        raw = make_raw(service_data=_sd(LOCK_LOCKED_CLOSED))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["lock_state"] == "locked"

    def test_unlocked(self, parser):
        raw = make_raw(service_data=_sd(LOCK_UNLOCKED_OPEN))
        result = parser.parse(raw)
        assert result.metadata["lock_state"] == "unlocked"

    def test_jammed(self, parser):
        raw = make_raw(service_data=_sd(LOCK_JAMMED))
        result = parser.parse(raw)
        assert result.metadata["lock_state"] == "jammed"

    def test_door_closed(self, parser):
        raw = make_raw(service_data=_sd(LOCK_LOCKED_CLOSED))
        result = parser.parse(raw)
        assert result.metadata["door_state"] == "closed"

    def test_door_open(self, parser):
        raw = make_raw(service_data=_sd(LOCK_UNLOCKED_OPEN))
        result = parser.parse(raw)
        assert result.metadata["door_state"] == "open"

    def test_battery(self, parser):
        raw = make_raw(service_data=_sd(LOCK_LOCKED_CLOSED))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 80

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(LOCK_LOCKED_CLOSED))
        result = parser.parse(raw)
        assert result.device_class == "lock"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(LOCK_LOCKED_CLOSED))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "lock"


class TestHumidifier:
    def test_power_on(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["power"] == "on"

    def test_power_off(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_OFF))
        result = parser.parse(raw)
        assert result.metadata["power"] == "off"

    def test_mode_auto(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result.metadata["mode"] == "auto"

    def test_mode_low(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_OFF))
        result = parser.parse(raw)
        assert result.metadata["mode"] == "low"

    def test_mode_high(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_WATER_LOW))
        result = parser.parse(raw)
        assert result.metadata["mode"] == "high"

    def test_humidity_setting(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result.metadata["humidity_setting"] == 55

    def test_water_low_true(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_WATER_LOW))
        result = parser.parse(raw)
        assert result.metadata["water_low"] is True

    def test_water_low_false(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result.metadata["water_low"] is False

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "humidifier"


class TestColorBulb:
    def test_power_on(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_WHITE))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["power"] == "on"

    def test_power_off(self, parser):
        raw = make_raw(service_data=_sd(BULB_OFF))
        result = parser.parse(raw)
        assert result.metadata["power"] == "off"

    def test_brightness(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_WHITE))
        result = parser.parse(raw)
        assert result.metadata["brightness"] == 80

    def test_color_mode_white(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_WHITE))
        result = parser.parse(raw)
        assert result.metadata["color_mode"] == "white"

    def test_color_mode_color(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_COLOR))
        result = parser.parse(raw)
        assert result.metadata["color_mode"] == "color"

    def test_color_mode_scene(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_SCENE))
        result = parser.parse(raw)
        assert result.metadata["color_mode"] == "scene"

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_WHITE))
        result = parser.parse(raw)
        assert result.device_class == "light"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_WHITE))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "color_bulb"


class TestBlindTilt:
    def test_calibrated(self, parser):
        raw = make_raw(service_data=_sd(BLIND_OPEN))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["calibrated"] is True

    def test_not_calibrated(self, parser):
        raw = make_raw(service_data=_sd(BLIND_UNCALIBRATED))
        result = parser.parse(raw)
        assert result.metadata["calibrated"] is False

    def test_position_open(self, parser):
        raw = make_raw(service_data=_sd(BLIND_OPEN))
        result = parser.parse(raw)
        assert result.metadata["position"] == 0

    def test_position_closed(self, parser):
        raw = make_raw(service_data=_sd(BLIND_CLOSED))
        result = parser.parse(raw)
        assert result.metadata["position"] == 100

    def test_direction_up(self, parser):
        raw = make_raw(service_data=_sd(BLIND_OPEN))
        result = parser.parse(raw)
        assert result.metadata["direction"] == "up"

    def test_direction_down(self, parser):
        raw = make_raw(service_data=_sd(BLIND_CLOSED))
        result = parser.parse(raw)
        assert result.metadata["direction"] == "down"

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(BLIND_OPEN))
        result = parser.parse(raw)
        assert result.device_class == "cover"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(BLIND_OPEN))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "blind_tilt"


class TestHub2:
    def test_temperature(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NORMAL))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(22.5)

    def test_negative_temperature(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NEG_TEMP))
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-3.2)

    def test_humidity(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NORMAL))
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == 55

    def test_light_level(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NORMAL))
        result = parser.parse(raw)
        assert result.metadata["light_level"] == 10

    def test_max_light(self, parser):
        raw = make_raw(service_data=_sd(HUB2_BRIGHT))
        result = parser.parse(raw)
        assert result.metadata["light_level"] == 20

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NORMAL))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NORMAL))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "hub2"


class TestOutdoorMeter:
    def test_temperature(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NORMAL))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(18.6)

    def test_negative_temperature(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NEG))
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-10.1)

    def test_humidity(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NORMAL))
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == 65

    def test_battery(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NORMAL))
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 90

    def test_device_class(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NORMAL))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_device_type(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NORMAL))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "outdoor_meter"


class TestDeviceClass:
    def test_meter_device_class(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_bot_device_class(self, parser):
        raw = make_raw(service_data=_sd(BOT_PRESS_OFF))
        result = parser.parse(raw)
        assert result.device_class == "switch"

    def test_curtain_device_class(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_OPEN))
        result = parser.parse(raw)
        assert result.device_class == "cover"

    def test_contact_device_class(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_CLOSED_NO_MOTION))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_motion_device_class(self, parser):
        raw = make_raw(service_data=_sd(MOTION_DETECTED))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_plug_mini_device_class(self, parser):
        raw = make_raw(service_data=_sd(PLUG_ON_50W))
        result = parser.parse(raw)
        assert result.device_class == "switch"

    def test_lock_device_class(self, parser):
        raw = make_raw(service_data=_sd(LOCK_LOCKED_CLOSED))
        result = parser.parse(raw)
        assert result.device_class == "lock"

    def test_humidifier_device_class(self, parser):
        raw = make_raw(service_data=_sd(HUMIDIFIER_ON_AUTO))
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_color_bulb_device_class(self, parser):
        raw = make_raw(service_data=_sd(BULB_ON_WHITE))
        result = parser.parse(raw)
        assert result.device_class == "light"

    def test_blind_tilt_device_class(self, parser):
        raw = make_raw(service_data=_sd(BLIND_OPEN))
        result = parser.parse(raw)
        assert result.device_class == "cover"

    def test_hub2_device_class(self, parser):
        raw = make_raw(service_data=_sd(HUB2_NORMAL))
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_outdoor_meter_device_class(self, parser):
        raw = make_raw(service_data=_sd(OUTDOOR_NORMAL))
        result = parser.parse(raw)
        assert result.device_class == "sensor"


class TestFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.parser_name == "switchbot"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.beacon_type == "switchbot"

    def test_device_type_meter(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "meter"

    def test_device_type_bot(self, parser):
        raw = make_raw(service_data=_sd(BOT_PRESS_OFF))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "bot"

    def test_device_type_curtain(self, parser):
        raw = make_raw(service_data=_sd(CURTAIN_OPEN))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "curtain"

    def test_device_type_contact(self, parser):
        raw = make_raw(service_data=_sd(CONTACT_CLOSED_NO_MOTION))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "contact_sensor"

    def test_device_type_motion(self, parser):
        raw = make_raw(service_data=_sd(MOTION_DETECTED))
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "motion_sensor"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert result.raw_payload_hex == METER_VALID.hex()


class TestIdentity:
    def test_identity_hash_from_mac(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(service_data=_sd(METER_VALID))
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex


class TestRejectsInvalid:
    def test_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_empty_service_data(self, parser):
        raw = make_raw(service_data={})
        assert parser.parse(raw) is None

    def test_wrong_uuid(self, parser):
        raw = make_raw(service_data={"0000fe95-0000-1000-8000-00805f9b34fb": b"\x54\x00\x00\x00\x00"})
        assert parser.parse(raw) is None

    def test_too_short_payload(self, parser):
        raw = make_raw(service_data=_sd(b"\x54"))
        assert parser.parse(raw) is None

    def test_empty_payload(self, parser):
        raw = make_raw(service_data=_sd(b""))
        assert parser.parse(raw) is None

    def test_unknown_device_type(self, parser):
        # Unknown device type byte should return None or handle gracefully
        raw = make_raw(service_data=_sd(b"\xFF\x00\x00\x00\x00"))
        assert parser.parse(raw) is None


class TestRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = SwitchBotParser()
        reg.register(
            name="switchbot",
            service_uuid="0000fd3d-0000-1000-8000-00805f9b34fb",
            company_id=0x0969,
            local_name_pattern=r"^W",
            description="SwitchBot",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(
            service_data=_sd(METER_VALID),
            service_uuids=[SWITCHBOT_UUID],
        )
        matched = reg.match(raw)
        assert any(isinstance(p, SwitchBotParser) for p in matched)

    def test_registered_matches_local_name(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = SwitchBotParser()
        reg.register(
            name="switchbot",
            service_uuid="0000fd3d-0000-1000-8000-00805f9b34fb",
            company_id=0x0969,
            local_name_pattern=r"^W",
            description="SwitchBot",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(service_data=None, local_name="WoHand")
        matched = reg.match(raw)
        assert any(isinstance(p, SwitchBotParser) for p in matched)
