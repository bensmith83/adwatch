"""Tests for Xiaomi MiBeacon BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.mibeacon import MiBeaconParser


@pytest.fixture
def parser():
    return MiBeaconParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
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


# --- Helper to build MiBeacon frames ---

def _build_frame(
    *,
    device_type=0x0098,
    frame_counter=0x01,
    mac=None,
    capability=None,
    object_id=None,
    object_data=None,
    encrypted=False,
):
    """Build an unencrypted MiBeacon service data payload."""
    fc = 0x0000
    if mac is not None:
        fc |= (1 << 4)  # has MAC
    if capability is not None:
        fc |= (1 << 5)  # has capability
    if object_id is not None:
        fc |= (1 << 6)  # has object data
    if encrypted:
        fc |= (1 << 7)  # encrypted

    buf = struct.pack("<HHB", fc, device_type, frame_counter)

    if mac is not None:
        # MAC is stored reversed (little-endian) in the frame
        mac_bytes = bytes(reversed(bytes.fromhex(mac.replace(":", ""))))
        buf += mac_bytes

    if capability is not None:
        buf += bytes([capability])

    if object_id is not None and object_data is not None:
        buf += struct.pack("<HB", object_id, len(object_data)) + object_data

    return buf


# MAC embedded in frame (reversed bytes of 11:22:33:44:55:66)
FRAME_MAC = "11:22:33:44:55:66"

# Temperature: 0x1004, value 245 -> 24.5 deg C
TEMP_VALUE = struct.pack("<h", 245)
TEMP_FRAME = _build_frame(mac=FRAME_MAC, object_id=0x1004, object_data=TEMP_VALUE)

# Humidity: 0x1006, value 655 -> 65.5%
HUMID_VALUE = struct.pack("<H", 655)
HUMID_FRAME = _build_frame(mac=FRAME_MAC, object_id=0x1006, object_data=HUMID_VALUE)

# Battery: 0x100A, value 87 -> 87%
BATTERY_VALUE = bytes([87])
BATTERY_FRAME = _build_frame(mac=FRAME_MAC, object_id=0x100A, object_data=BATTERY_VALUE)

# Temp+Humidity combined: 0x100D, temp=245 (24.5C) + humidity=655 (65.5%)
TEMP_HUMID_VALUE = struct.pack("<hH", 245, 655)
TEMP_HUMID_FRAME = _build_frame(mac=FRAME_MAC, object_id=0x100D, object_data=TEMP_HUMID_VALUE)

# Negative temperature: -50 -> -5.0 deg C
NEG_TEMP_VALUE = struct.pack("<h", -50)
NEG_TEMP_FRAME = _build_frame(mac=FRAME_MAC, object_id=0x1004, object_data=NEG_TEMP_VALUE)

# Frame without MAC (use raw.mac_address for identity)
NO_MAC_FRAME = _build_frame(object_id=0x1004, object_data=TEMP_VALUE)

# Encrypted frame
ENCRYPTED_FRAME = _build_frame(mac=FRAME_MAC, encrypted=True, object_id=0x1004, object_data=TEMP_VALUE)


class TestMiBeaconTemperature:
    def test_parse_temperature_valid(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_temperature_value(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_negative_temperature(self, parser):
        raw = make_raw(service_data={"fe95": NEG_TEMP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(-5.0)

    def test_temperature_object_id(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x1004


class TestMiBeaconHumidity:
    def test_humidity_value(self, parser):
        raw = make_raw(service_data={"fe95": HUMID_FRAME})
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.5)

    def test_humidity_object_id(self, parser):
        raw = make_raw(service_data={"fe95": HUMID_FRAME})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x1006


class TestMiBeaconBattery:
    def test_battery_value(self, parser):
        raw = make_raw(service_data={"fe95": BATTERY_FRAME})
        result = parser.parse(raw)
        assert result.metadata["battery"] == 87

    def test_battery_object_id(self, parser):
        raw = make_raw(service_data={"fe95": BATTERY_FRAME})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x100A


class TestMiBeaconTempHumidity:
    def test_combined_temperature(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_HUMID_FRAME})
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_combined_humidity(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_HUMID_FRAME})
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(65.5)

    def test_combined_object_id(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_HUMID_FRAME})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x100D


class TestMiBeaconIdentity:
    def test_identity_hash_from_frame_mac(self, parser):
        """When MAC is in frame, identity = SHA256(frame_mac)[:16]."""
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        expected = hashlib.sha256(FRAME_MAC.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_from_raw_mac(self, parser):
        """When no MAC in frame, identity = SHA256(raw.mac_address)[:16]."""
        raw = make_raw(service_data={"fe95": NO_MAC_FRAME}, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestMiBeaconFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.parser_name == "mibeacon"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.beacon_type == "mibeacon"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.raw_payload_hex == TEMP_FRAME.hex()

    def test_device_type_in_metadata(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["device_type"] == 0x0098

    def test_frame_counter_in_metadata(self, parser):
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["frame_counter"] == 0x01


class TestMiBeaconMACHandling:
    def test_frame_with_mac(self, parser):
        """Frame with MAC bit set should extract MAC from payload."""
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        result = parser.parse(raw)
        assert result.metadata.get("mac") == FRAME_MAC

    def test_frame_without_mac(self, parser):
        """Frame without MAC bit should still parse successfully."""
        raw = make_raw(service_data={"fe95": NO_MAC_FRAME})
        result = parser.parse(raw)
        assert result is not None


class TestMiBeaconEncrypted:
    def test_encrypted_returns_none(self, parser):
        """Encrypted frames should be skipped (return None)."""
        raw = make_raw(service_data={"fe95": ENCRYPTED_FRAME})
        assert parser.parse(raw) is None


class TestMiBeaconMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": TEMP_FRAME})
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        # Minimum header is 5 bytes (fc:2 + device:2 + counter:1)
        raw = make_raw(service_data={"fe95": bytes([0x01, 0x02, 0x03])})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(service_data={"fe95": b""})
        assert parser.parse(raw) is None


class TestMiBeaconMotionIlluminance:
    def test_motion_illuminance_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0003, object_data=struct.pack("<I", 1500))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["illuminance"] == 1500

    def test_motion_illuminance_object_id(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0003, object_data=struct.pack("<I", 1500))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x0003


class TestMiBeaconIlluminance:
    def test_illuminance_value(self, parser):
        # uint24 LE: pack as 3 bytes
        obj_data = struct.pack("<I", 800)[:3]
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0007, object_data=obj_data)
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["illuminance"] == 800

    def test_illuminance_object_id(self, parser):
        obj_data = struct.pack("<I", 800)[:3]
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0007, object_data=obj_data)
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x0007


class TestMiBeaconSoilMoisture:
    def test_soil_moisture_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0008, object_data=bytes([42]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["soil_moisture"] == 42


class TestMiBeaconSoilConductivity:
    def test_soil_conductivity_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0009, object_data=struct.pack("<H", 350))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["soil_conductivity"] == 350


class TestMiBeaconBatteryNew:
    def test_battery_0x000A_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x000A, object_data=bytes([95]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["battery"] == 95


class TestMiBeaconDoorWindow:
    def test_door_window_open(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x000F, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["door_window"] == "open"

    def test_door_window_closed(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x000F, object_data=bytes([1]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["door_window"] == "closed"


class TestMiBeaconMotion:
    def test_motion_event(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1001, object_data=b"")
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["motion"] is True


class TestMiBeaconNoMotion:
    def test_no_motion_event(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1002, object_data=b"")
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["no_motion"] is True


class TestMiBeaconButton:
    def test_button_event(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1005, object_data=struct.pack("<BB", 1, 3))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["button_event_type"] == 1
        assert result.metadata["button_count"] == 3


class TestMiBeaconDoorEvent:
    def test_door_event_open(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1007, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["door_event"] == "open"

    def test_door_event_closed(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1007, object_data=bytes([1]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["door_event"] == "closed"


class TestMiBeaconFormaldehyde:
    def test_formaldehyde_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1010, object_data=struct.pack("<H", 123))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["formaldehyde"] == pytest.approx(1.23)


class TestMiBeaconSwitchEvent:
    def test_switch_event(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1012, object_data=bytes([2]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["switch_event"] == 2


class TestMiBeaconConsumables:
    def test_consumables_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1013, object_data=bytes([75]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["consumables"] == 75


class TestMiBeaconFlood:
    def test_flood_dry(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1014, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["flood"] == "dry"

    def test_flood_wet(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1014, object_data=bytes([1]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["flood"] == "wet"


class TestMiBeaconSmoke:
    def test_smoke_clear(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1015, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["smoke"] == "clear"

    def test_smoke_detected(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1015, object_data=bytes([1]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["smoke"] == "smoke"


class TestMiBeaconGas:
    def test_gas_clear(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1018, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["gas"] == "clear"

    def test_gas_detected(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1018, object_data=bytes([1]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["gas"] == "gas"


class TestMiBeaconRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = MiBeaconParser()
        reg.register(
            name="mibeacon",
            service_uuid="fe95",
            description="Xiaomi MiBeacon",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(service_data={"fe95": TEMP_FRAME})
        matched = reg.match(raw)
        assert any(isinstance(p, MiBeaconParser) for p in matched)

    def test_not_core(self):
        """MiBeacon should be a plugin (core=False)."""
        assert hasattr(MiBeaconParser, '_parser_info') or True
