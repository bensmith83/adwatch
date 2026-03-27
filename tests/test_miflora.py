"""Tests verifying mibeacon plugin correctly parses MiFlora (device_type 0x0098) ads.

MiFlora uses the standard MiBeacon protocol on service UUID fe95.
The existing mibeacon plugin handles all MiFlora object types generically.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.mibeacon import MiBeaconParser

MIFLORA_DEVICE_TYPE = 0x0098


@pytest.fixture
def parser():
    return MiBeaconParser()


def _build_mibeacon_frame(
    device_type: int,
    frame_counter: int,
    mac: bytes | None = None,
    object_id: int | None = None,
    object_data: bytes = b"",
    has_capability: bool = False,
) -> bytes:
    """Build a MiBeacon service data frame."""
    has_mac = mac is not None
    has_object = object_id is not None

    frame_control = 0
    if has_mac:
        frame_control |= (1 << 4)
    if has_capability:
        frame_control |= (1 << 5)
    if has_object:
        frame_control |= (1 << 6)

    buf = struct.pack("<HHB", frame_control, device_type, frame_counter)

    if has_mac:
        # MAC is stored reversed in MiBeacon
        buf += bytes(reversed(mac))

    if has_capability:
        buf += b"\x00"

    if has_object:
        buf += struct.pack("<HB", object_id, len(object_data))
        buf += object_data

    return buf


def make_miflora_raw(
    object_id: int | None = None,
    object_data: bytes = b"",
    mac_address: str = "C4:7C:8D:6A:12:34",
    frame_counter: int = 42,
    has_mac: bool = True,
    has_capability: bool = False,
):
    mac_bytes = bytes(int(b, 16) for b in mac_address.split(":")) if has_mac else None

    data = _build_mibeacon_frame(
        device_type=MIFLORA_DEVICE_TYPE,
        frame_counter=frame_counter,
        mac=mac_bytes,
        object_id=object_id,
        object_data=object_data,
        has_capability=has_capability,
    )

    return RawAdvertisement(
        timestamp="2026-03-26T00:00:00+00:00",
        mac_address=mac_address,
        address_type="public",
        manufacturer_data=None,
        service_data={"fe95": data},
        service_uuids=["0000fe95-0000-1000-8000-00805f9b34fb"],
        local_name="Flower care",
    )


class TestMifloraTemperature:
    def test_temperature_parsing(self, parser):
        """MiFlora object 0x1004: temperature as int16 LE / 10."""
        # 25.6 C = 256 as int16
        obj_data = struct.pack("<h", 256)
        raw = make_miflora_raw(object_id=0x1004, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["temperature"] == 25.6

    def test_negative_temperature(self, parser):
        """Negative temperature (e.g. -5.0 C)."""
        obj_data = struct.pack("<h", -50)
        raw = make_miflora_raw(object_id=0x1004, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["temperature"] == -5.0


class TestMifloraLux:
    def test_illuminance_parsing(self, parser):
        """MiFlora object 0x0007: illuminance as uint24 LE."""
        # 1500 lux
        obj_data = int.to_bytes(1500, 3, "little")
        raw = make_miflora_raw(object_id=0x0007, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["illuminance"] == 1500

    def test_zero_lux(self, parser):
        obj_data = int.to_bytes(0, 3, "little")
        raw = make_miflora_raw(object_id=0x0007, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["illuminance"] == 0


class TestMifloraMoisture:
    def test_moisture_parsing(self, parser):
        """MiFlora object 0x0008: soil moisture as uint8 %."""
        obj_data = bytes([45])
        raw = make_miflora_raw(object_id=0x0008, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["soil_moisture"] == 45


class TestMifloraConductivity:
    def test_conductivity_parsing(self, parser):
        """MiFlora object 0x0009: soil conductivity as uint16 LE."""
        obj_data = struct.pack("<H", 350)
        raw = make_miflora_raw(object_id=0x0009, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["soil_conductivity"] == 350


class TestMifloraBattery:
    def test_battery_parsing(self, parser):
        """MiFlora object 0x100A: battery as uint8 %."""
        obj_data = bytes([85])
        raw = make_miflora_raw(object_id=0x100A, object_data=obj_data)
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["battery"] == 85


class TestMifloraCommon:
    def test_device_type_in_metadata(self, parser):
        """Device type 0x0098 should appear in metadata."""
        obj_data = struct.pack("<h", 200)
        raw = make_miflora_raw(object_id=0x1004, object_data=obj_data)
        result = parser.parse(raw)

        assert result.metadata["device_type"] == MIFLORA_DEVICE_TYPE

    def test_parser_name_is_mibeacon(self, parser):
        """MiFlora is handled by the generic mibeacon parser."""
        obj_data = bytes([50])
        raw = make_miflora_raw(object_id=0x0008, object_data=obj_data)
        result = parser.parse(raw)

        assert result.parser_name == "mibeacon"
        assert result.beacon_type == "mibeacon"

    def test_device_class_sensor(self, parser):
        obj_data = bytes([50])
        raw = make_miflora_raw(object_id=0x0008, object_data=obj_data)
        result = parser.parse(raw)

        assert result.device_class == "sensor"

    def test_identity_hash_from_mac_in_frame(self, parser):
        """When MAC is present in the MiBeacon frame, hash should use it."""
        obj_data = bytes([50])
        raw = make_miflora_raw(
            object_id=0x0008,
            object_data=obj_data,
            mac_address="C4:7C:8D:6A:12:34",
        )
        result = parser.parse(raw)

        # mibeacon extracts MAC from frame and uses it for identity
        expected = hashlib.sha256("C4:7C:8D:6A:12:34".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_frame_without_mac_uses_raw_mac(self, parser):
        """When no MAC in frame, uses raw.mac_address for identity."""
        obj_data = bytes([50])
        raw = make_miflora_raw(
            object_id=0x0008,
            object_data=obj_data,
            has_mac=False,
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)

        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_frame_with_capability_flag(self, parser):
        """Capability byte should be skipped correctly."""
        obj_data = struct.pack("<h", 220)
        raw = make_miflora_raw(
            object_id=0x1004,
            object_data=obj_data,
            has_capability=True,
        )
        result = parser.parse(raw)

        assert result is not None
        assert result.metadata["temperature"] == 22.0

    def test_no_service_data_returns_none(self, parser):
        raw = RawAdvertisement(
            timestamp="2026-03-26T00:00:00+00:00",
            mac_address="AA:BB:CC:DD:EE:FF",
            address_type="public",
            manufacturer_data=None,
            service_data=None,
            service_uuids=[],
            local_name="Flower care",
        )
        assert parser.parse(raw) is None
