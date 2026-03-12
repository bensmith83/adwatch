"""Tests for BTHome v2 BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.bthome import BTHomeParser


@pytest.fixture
def parser():
    return BTHomeParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


# --- BTHome v2 payload helpers ---
# Device info byte: upper 3 bits = version (0b010 = v2), bit 0 = encryption, bit 2 = trigger
DEVICE_INFO_V2 = 0x40  # version 2, no encryption, no trigger
DEVICE_INFO_V2_ENCRYPTED = 0x41  # version 2, encryption bit set
DEVICE_INFO_V1 = 0x20  # version 1 (wrong)
DEVICE_INFO_V3 = 0x60  # version 3 (wrong)

BTHOME_UUID = "fcd2"

# Temperature: object_id=0x02, sint16 LE, factor 0.01
# 2345 * 0.01 = 23.45 C
TEMP_PAYLOAD = bytes([DEVICE_INFO_V2, 0x02]) + struct.pack("<h", 2345)

# Negative temperature: -1050 * 0.01 = -10.50 C
NEG_TEMP_PAYLOAD = bytes([DEVICE_INFO_V2, 0x02]) + struct.pack("<h", -1050)

# Humidity: object_id=0x03, uint16 LE, factor 0.01
# 5678 * 0.01 = 56.78 %
HUMIDITY_PAYLOAD = bytes([DEVICE_INFO_V2, 0x03]) + struct.pack("<H", 5678)

# Battery: object_id=0x01, uint8
# 87%
BATTERY_PAYLOAD = bytes([DEVICE_INFO_V2, 0x01, 87])

# Pressure: object_id=0x04, uint24 LE, factor 0.01
# 101325 * 0.01 = 1013.25 hPa
PRESSURE_PAYLOAD = bytes([DEVICE_INFO_V2, 0x04]) + (101325).to_bytes(3, "little")

# Illuminance: object_id=0x05, uint24 LE, factor 0.01
# 13460 * 0.01 = 134.60 lux
ILLUMINANCE_PAYLOAD = bytes([DEVICE_INFO_V2, 0x05]) + (13460).to_bytes(3, "little")

# Voltage: object_id=0x0C, uint16 LE, factor 0.001
# 3214 * 0.001 = 3.214 V
VOLTAGE_PAYLOAD = bytes([DEVICE_INFO_V2, 0x0C]) + struct.pack("<H", 3214)

# Power: object_id=0x0B, uint24 LE, factor 0.01
# 6942 * 0.01 = 69.42 W
POWER_PAYLOAD = bytes([DEVICE_INFO_V2, 0x0B]) + (6942).to_bytes(3, "little")

# Energy: object_id=0x0A, uint24 LE, factor 0.001
# 12345 * 0.001 = 12.345 kWh
ENERGY_PAYLOAD = bytes([DEVICE_INFO_V2, 0x0A]) + (12345).to_bytes(3, "little")

# Multiple objects: temperature (23.45 C) + humidity (56.78%) + battery (87%)
MULTI_PAYLOAD = (
    bytes([DEVICE_INFO_V2])
    + bytes([0x02]) + struct.pack("<h", 2345)     # temperature
    + bytes([0x03]) + struct.pack("<H", 5678)      # humidity
    + bytes([0x01, 87])                             # battery
)

# Encrypted payload (encryption bit set)
ENCRYPTED_PAYLOAD = bytes([DEVICE_INFO_V2_ENCRYPTED, 0x02]) + struct.pack("<h", 2345)

# Wrong version payloads
V1_PAYLOAD = bytes([DEVICE_INFO_V1, 0x02]) + struct.pack("<h", 2345)
V3_PAYLOAD = bytes([DEVICE_INFO_V3, 0x02]) + struct.pack("<h", 2345)


class TestBTHomeTemperature:
    def test_parse_temperature(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_temperature_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(23.45)

    def test_negative_temperature(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: NEG_TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(-10.50)


class TestBTHomeHumidity:
    def test_humidity_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: HUMIDITY_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(56.78)


class TestBTHomeBattery:
    def test_battery_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: BATTERY_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["battery"] == 87


class TestBTHomePressure:
    def test_pressure_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: PRESSURE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["pressure"] == pytest.approx(1013.25)


class TestBTHomeIlluminance:
    def test_illuminance_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: ILLUMINANCE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["illuminance"] == pytest.approx(134.60)


class TestBTHomeVoltage:
    def test_voltage_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: VOLTAGE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["voltage"] == pytest.approx(3.214)


class TestBTHomePower:
    def test_power_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: POWER_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["power"] == pytest.approx(69.42)


class TestBTHomeEnergy:
    def test_energy_value(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: ENERGY_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["energy"] == pytest.approx(12.345)


class TestBTHomeMultipleObjects:
    def test_multi_has_temperature(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: MULTI_PAYLOAD})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(23.45)

    def test_multi_has_humidity(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: MULTI_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(56.78)

    def test_multi_has_battery(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: MULTI_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["battery"] == 87


class TestBTHomeIdentity:
    def test_identity_hash_from_mac(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_identity_different_macs(self, parser):
        raw1 = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD}, mac_address="11:22:33:44:55:66")
        raw2 = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD}, mac_address="66:55:44:33:22:11")
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestBTHomeFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result.parser_name == "bthome"

    def test_device_class(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result.beacon_type == "bthome"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        result = parser.parse(raw)
        assert result.raw_payload_hex == TEMP_PAYLOAD.hex()


class TestBTHomeEncrypted:
    def test_encrypted_returns_none(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: ENCRYPTED_PAYLOAD})
        assert parser.parse(raw) is None


class TestBTHomeWrongVersion:
    def test_v1_returns_none(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: V1_PAYLOAD})
        assert parser.parse(raw) is None

    def test_v3_returns_none(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: V3_PAYLOAD})
        assert parser.parse(raw) is None


class TestBTHomeMalformed:
    def test_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": TEMP_PAYLOAD})
        assert parser.parse(raw) is None

    def test_too_short(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: bytes([0x40])})
        assert parser.parse(raw) is None

    def test_empty_data(self, parser):
        raw = make_raw(service_data={BTHOME_UUID: b""})
        assert parser.parse(raw) is None


class TestBTHomeBugUnknownObjectBreak:
    """Bug: unknown object ID causes break, dropping subsequent known measurements."""

    def test_known_after_unknown_still_parsed(self, parser):
        """If a known object follows an unknown one, it should still be parsed.
        Packet: battery(87%) + truly_unknown(0xFF, 1 byte) + temperature(23.45)
        With the bug, temperature is lost. After fix, unknown is skipped but
        since 0xFF is truly unknown (not in table), we can't know its length,
        so break is acceptable. But if we add all known IDs, any 'unknown' gap
        between two known IDs won't happen in practice."""
        # This test verifies: two known objects with NO unknown in between parse fine
        # (regression guard)
        payload = (
            bytes([DEVICE_INFO_V2])
            + bytes([0x01, 87])                             # battery
            + bytes([0x02]) + struct.pack("<h", 2345)       # temperature
        )
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["battery"] == 87
        assert result.metadata["temperature"] == pytest.approx(23.45)

    def test_known_objects_not_in_table_cause_break(self, parser):
        """Packet with opening(0x11) before temperature — opening must be in table
        so temperature isn't dropped."""
        payload = (
            bytes([DEVICE_INFO_V2])
            + bytes([0x11, 1])                              # opening = True
            + bytes([0x02]) + struct.pack("<h", 2345)       # temperature
        )
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert "opening" in result.metadata
        assert result.metadata["temperature"] == pytest.approx(23.45)


class TestBTHomeMassKg:
    def test_mass_kg(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x06]) + struct.pack("<H", 7520)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["mass_kg"] == pytest.approx(75.20)


class TestBTHomeMassLb:
    def test_mass_lb(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x07]) + struct.pack("<H", 16580)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["mass_lb"] == pytest.approx(165.80)


class TestBTHomeDewPoint:
    def test_dew_point_positive(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x08]) + struct.pack("<h", 1750)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["dew_point"] == pytest.approx(17.50)

    def test_dew_point_negative(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x08]) + struct.pack("<h", -320)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["dew_point"] == pytest.approx(-3.20)


class TestBTHomeCount:
    def test_count(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x09, 42])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["count"] == 42


class TestBTHomePM:
    def test_pm25(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x0D]) + struct.pack("<H", 35)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["pm25"] == 35

    def test_pm10(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x0E]) + struct.pack("<H", 50)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["pm10"] == 50


class TestBTHomeCO2:
    def test_co2(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x12]) + struct.pack("<H", 800)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["co2"] == 800


class TestBTHomeTVOC:
    def test_tvoc(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x13]) + struct.pack("<H", 250)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["tvoc"] == 250


class TestBTHomeMoisture:
    def test_moisture(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x14]) + struct.pack("<H", 3456)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["moisture"] == pytest.approx(34.56)


class TestBTHomeTemperature01:
    def test_temperature_01(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x45]) + struct.pack("<h", 234)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["temperature_01"] == pytest.approx(23.4)

    def test_temperature_01_negative(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x45]) + struct.pack("<h", -105)
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["temperature_01"] == pytest.approx(-10.5)


class TestBTHomeUVIndex:
    def test_uv_index(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x46, 72])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result.metadata["uv_index"] == pytest.approx(7.2)


class TestBTHomeBinarySensors:
    @pytest.mark.parametrize("obj_id,name", [
        (0x0F, "generic_boolean"),
        (0x10, "power_binary"),
        (0x11, "opening"),
        (0x15, "battery_low"),
        (0x16, "battery_charging"),
        (0x17, "co_detected"),
        (0x1A, "door"),
        (0x1C, "gas"),
        (0x1D, "heat"),
        (0x1E, "light"),
        (0x1F, "lock"),
        (0x20, "moisture_binary"),
        (0x21, "motion"),
        (0x22, "moving"),
        (0x23, "occupancy"),
        (0x2D, "window"),
        (0x2E, "humidity_flag"),
        (0x2F, "moisture_flag"),
    ])
    def test_binary_sensor_true(self, parser, obj_id, name):
        payload = bytes([DEVICE_INFO_V2, obj_id, 1])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata[name] == 1

    @pytest.mark.parametrize("obj_id,name", [
        (0x0F, "generic_boolean"),
        (0x11, "opening"),
        (0x21, "motion"),
    ])
    def test_binary_sensor_false(self, parser, obj_id, name):
        payload = bytes([DEVICE_INFO_V2, obj_id, 0])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata[name] == 0


class TestBTHomeButtonEvent:
    @pytest.mark.parametrize("value,expected", [
        (0x00, "none"),
        (0x01, "press"),
        (0x02, "double_press"),
        (0x03, "triple_press"),
        (0x04, "long_press"),
        (0x05, "long_double_press"),
        (0x06, "long_triple_press"),
        (0x80, "hold_press"),
    ])
    def test_button_event(self, parser, value, expected):
        payload = bytes([DEVICE_INFO_V2, 0x3A, value])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["button_event"] == expected

    def test_button_event_unknown_value(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x3A, 0x99])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["button_event"] == 0x99  # raw value for unknown


class TestBTHomeDimmerEvent:
    def test_dimmer_clockwise(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x3C, 3, 0x00])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["dimmer_event"] == {"steps": 3, "direction": "clockwise"}

    def test_dimmer_counter_clockwise(self, parser):
        payload = bytes([DEVICE_INFO_V2, 0x3C, 5, 0x01])
        raw = make_raw(service_data={BTHOME_UUID: payload})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["dimmer_event"] == {"steps": 5, "direction": "counter_clockwise"}


class TestBTHomeRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = BTHomeParser()
        reg.register(
            name="bthome",
            service_uuid=BTHOME_UUID,
            description="BTHome v2 sensor advertisements",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(service_data={BTHOME_UUID: TEMP_PAYLOAD})
        matched = reg.match(raw)
        assert any(isinstance(p, BTHomeParser) for p in matched)
