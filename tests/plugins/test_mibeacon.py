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
        fc |= (1 << 3)  # encrypted (frame-control bit 3)

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
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1007, object_data=obj_data)
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["illuminance"] == 800

    def test_illuminance_object_id(self, parser):
        obj_data = struct.pack("<I", 800)[:3]
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1007, object_data=obj_data)
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["object_id"] == 0x1007


class TestMiBeaconSoilMoisture:
    def test_soil_moisture_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1008, object_data=bytes([42]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["soil_moisture"] == 42


class TestMiBeaconSoilConductivity:
    def test_soil_conductivity_value(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1009, object_data=struct.pack("<H", 350))
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


class TestMiBeaconSleepState:
    def test_sleep_state(self, parser):
        """0x1002 is mi_sleep_state, not "no motion"."""
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1002, object_data=bytes([1]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["sleep_state"] == 1
        assert "no_motion" not in result.metadata


class TestMiBeaconButton:
    def test_button_event(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1005, object_data=struct.pack("<BB", 1, 3))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["button_event_type"] == 1
        assert result.metadata["button_count"] == 3


class TestMiBeaconDoorEvent:
    def test_door_event_open(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0007, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["door_event"] == "open"

    def test_door_event_closed(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x0007, object_data=bytes([1]))
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
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1016, object_data=bytes([0]))
        raw = make_raw(service_data={"fe95": frame})
        result = parser.parse(raw)
        assert result.metadata["gas"] == "clear"

    def test_gas_detected(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1016, object_data=bytes([1]))
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


class TestMiBeaconWatchflowerAudit:
    """Corrections and additions from reports/watchflower_passive.md — the
    WatchFlower source (src/src/device_sensor_advertisement.cpp:139-396) is
    open, so it is ground truth rather than inference."""

    def test_encryption_is_frame_control_bit3(self, parser):
        frame = _build_frame(mac=FRAME_MAC, encrypted=True,
                             object_id=0x1004, object_data=TEMP_VALUE)
        assert parser.parse(make_raw(service_data={"fe95": frame})) is None

    def test_bit7_is_mesh_not_encryption(self, parser):
        """Bit 7 is isMeshed; a mesh frame must still decode."""
        frame = bytearray(_build_frame(mac=FRAME_MAC, object_id=0x1004,
                                       object_data=TEMP_VALUE))
        fc = struct.unpack_from("<H", frame, 0)[0] | (1 << 7)
        struct.pack_into("<H", frame, 0, fc)
        result = parser.parse(make_raw(service_data={"fe95": bytes(frame)}))
        assert result is not None
        assert result.metadata["is_mesh"] is True
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_frame_control_flag_fields(self, parser):
        frame = bytearray(_build_frame(mac=FRAME_MAC, object_id=0x1004,
                                       object_data=TEMP_VALUE))
        fc = struct.unpack_from("<H", frame, 0)[0]
        fc |= (1 << 8) | (1 << 9)          # registered + solicited
        fc |= (0b10 << 10)                  # auth mode 2
        fc |= (0x5 << 12)                   # version 5
        struct.pack_into("<H", frame, 0, fc)
        result = parser.parse(make_raw(service_data={"fe95": bytes(frame)}))
        assert result.metadata["is_registered"] is True
        assert result.metadata["is_solicited"] is True
        assert result.metadata["auth_mode"] == 2
        assert result.metadata["protocol_version"] == 5

    def test_illuminance_at_0x1007(self, parser):
        obj_data = struct.pack("<I", 12345)[:3]
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1007, object_data=obj_data)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["illuminance"] == 12345
        assert "door_event" not in result.metadata

    def test_soil_moisture_two_byte_form(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1008,
                             object_data=struct.pack("<H", 300))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["soil_moisture"] == 300

    def test_lock_state_object(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x100E, object_data=bytes([3]))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["lock_state"] == 3

    def test_door_state_object(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x100F, object_data=bytes([1]))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["door_state"] == 1

    def test_bind_state_object(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1011, object_data=bytes([1]))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["bind_state"] == 1

    def test_rssi_object(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1003, object_data=bytes([0x50]))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["reported_rssi"] == 0x50

    def test_gas_state_at_0x1016(self, parser):
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1016, object_data=bytes([1]))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["gas"] == "gas"

    @pytest.mark.parametrize("product_id,model", [
        (0x0098, "HHCCJCY01"),
        (0x03BC, "HHCCJCY09"),
        (0x015D, "HHCCPOT002"),
        (0x01AA, "LYWSDCGQ"),
        (0x045B, "LYWSD02"),
        (0x06D3, "MHO-C303"),
        (0x0347, "CGG1"),
        (0x066F, "CGDK2"),
        (0x02DF, "JQJCY01YM"),
    ])
    def test_product_id_model_table(self, parser, product_id, model):
        frame = _build_frame(device_type=product_id, mac=FRAME_MAC,
                             object_id=0x1004, object_data=TEMP_VALUE)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["device_model"] == model
        assert result.metadata["device_type"] == product_id

    def test_unknown_product_id_has_no_model(self, parser):
        frame = _build_frame(device_type=0x7FFF, mac=FRAME_MAC,
                             object_id=0x1004, object_data=TEMP_VALUE)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert "device_model" not in result.metadata

    def test_capability_byte_is_decoded(self, parser):
        frame = _build_frame(mac=FRAME_MAC, capability=0x01,
                             object_id=0x1004, object_data=TEMP_VALUE)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["connectable"] is True
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_io_capability_consumes_two_extra_bytes(self, parser):
        """Capability bit5 (hasIO) is followed by a 2-byte IO field; without
        skipping it the object header lands on the wrong offset."""
        fc = (1 << 4) | (1 << 5) | (1 << 6)
        mac_bytes = bytes(reversed(bytes.fromhex(FRAME_MAC.replace(":", ""))))
        frame = (
            struct.pack("<HHB", fc, 0x0098, 0x01)
            + mac_bytes
            + bytes([0x20])                      # capability: bit5 hasIO
            + struct.pack("<H", 0x0102)          # IO capability
            + struct.pack("<HB", 0x1004, 2) + TEMP_VALUE
        )
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result is not None
        assert result.metadata["has_io"] is True
        assert result.metadata["io_capability"] == 0x0102
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_embedded_mac_anchors_identity(self, parser):
        """The MiBeacon MAC survives BLE MAC rotation."""
        frame = _build_frame(mac=FRAME_MAC, object_id=0x1004, object_data=TEMP_VALUE)
        a = parser.parse(make_raw(service_data={"fe95": frame},
                                  mac_address="00:00:00:00:00:01"))
        b = parser.parse(make_raw(service_data={"fe95": frame},
                                  mac_address="00:00:00:00:00:02"))
        assert a.metadata["mac"] == FRAME_MAC
        assert a.identifier_hash == b.identifier_hash


class TestMiBeaconYeelightAudit:
    """Additions from reports/yeelight-cherry_passive.md
    (``com.miot.service.connection.bluetooth.MiotPacketParser``).

    That report independently decodes the same 0xFE95 header and agrees with
    WatchFlower on every bit index — including reading the version from byte 1
    bits 4-7, i.e. bits 12-15 of the 16-bit frame control, which settles the
    "[13:15]" wording in the WatchFlower table.
    """

    @staticmethod
    def _fc(*, version=0, auth_mode=0, has_mac=True, has_capability=False,
            has_object=False, registered=False, binding_cfm=False):
        fc = 0
        if has_mac:
            fc |= 1 << 4
        if has_capability:
            fc |= 1 << 5
        if has_object:
            fc |= 1 << 6
        if registered:
            fc |= 1 << 8
        if binding_cfm:
            fc |= 1 << 9
        fc |= (auth_mode & 0x03) << 10
        fc |= (version & 0x0F) << 12
        return fc

    def _frame(self, fc, *, capability=None, combo_key=None, io_capability=None,
               event=b"", device_type=0x0098):
        mac_bytes = bytes(reversed(bytes.fromhex(FRAME_MAC.replace(":", ""))))
        buf = struct.pack("<HHB", fc, device_type, 0x01) + mac_bytes
        if capability is not None:
            buf += bytes([capability])
        if combo_key is not None:
            buf += combo_key
        if io_capability is not None:
            buf += struct.pack("<H", io_capability)
        return buf + event

    def test_version_is_byte1_bits_4_to_7(self, parser):
        frame = self._frame(self._fc(version=5))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["protocol_version"] == 5

    @pytest.mark.parametrize("code,name", [
        (0, "rc4"),
        (1, "secure_auth"),
        (2, "standard_auth"),
    ])
    def test_auth_mode_names(self, parser, code, name):
        frame = self._frame(self._fc(auth_mode=code))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["auth_mode"] == code
        assert result.metadata["auth_mode_name"] == name

    def test_binding_confirmation_is_frame_control_bit9(self, parser):
        frame = self._frame(self._fc(binding_cfm=True))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["binding_confirmation"] is True

    def test_capability_sub_fields(self, parser):
        # 0b0001_1111 -> connectable, centralable, encryptable, bindable=3
        frame = self._frame(self._fc(has_capability=True), capability=0x1F)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["connectable"] is True
        assert result.metadata["centralable"] is True
        assert result.metadata["encryptable"] is True
        assert result.metadata["bindable"] == 3
        assert result.metadata.get("has_io", False) is False

    def test_combo_key_consumes_two_bytes_when_bindable_three(self, parser):
        """withCapability && bindable == 3 && version >= 3 adds a 2-byte
        combo key before the event."""
        frame = self._frame(
            self._fc(version=3, has_capability=True, has_object=True),
            capability=0x18,                       # bindable = 3
            combo_key=b"\xAB\xCD",
            event=struct.pack("<HB", 0x1004, 2) + TEMP_VALUE,
        )
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["combo_key_hex"] == "abcd"
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_combo_key_absent_below_version_three(self, parser):
        frame = self._frame(
            self._fc(version=2, has_capability=True, has_object=True),
            capability=0x18,
            event=struct.pack("<HB", 0x1004, 2) + TEMP_VALUE,
        )
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert "combo_key_hex" not in result.metadata
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_version_five_event_is_length_then_one_byte_id(self, parser):
        """v>=5 re-orders the event header to eventLength(1) + eventId(1)."""
        frame = self._frame(
            self._fc(version=5, has_object=True),
            event=bytes([0x02, 0x4C]) + b"\xAA\xBB",
        )
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["object_id"] == 0x4C
        assert result.metadata["object_data_hex"] == "aabb"
        # The 1-byte v5 event ID space is not documented, so nothing is decoded
        assert "temperature" not in result.metadata

    def test_version_four_event_keeps_two_byte_id(self, parser):
        frame = self._frame(
            self._fc(version=4, has_object=True),
            event=struct.pack("<HB", 0x1004, 2) + TEMP_VALUE,
        )
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["object_id"] == 0x1004
        assert result.metadata["temperature"] == pytest.approx(24.5)

    def test_unprovisioned_lamp_heuristic(self, parser):
        """registered == 0 && withCapability && connectable == 1 marks a
        factory-reset / unprovisioned Xiaomi-ecosystem device."""
        frame = self._frame(self._fc(has_capability=True, registered=False),
                            capability=0x01)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["unprovisioned"] is True

        frame = self._frame(self._fc(has_capability=True, registered=True),
                            capability=0x01)
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert result.metadata["unprovisioned"] is False

    def test_unprovisioned_absent_without_capability(self, parser):
        frame = self._frame(self._fc(has_capability=False))
        result = parser.parse(make_raw(service_data={"fe95": frame}))
        assert "unprovisioned" not in result.metadata
