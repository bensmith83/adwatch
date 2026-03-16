"""Tests for iNode Energy Meter plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.inode_energy import INodeEnergyParser


DEVICE_TYPES = {
    "standard": 0x90,
    "light_sensor": 0x92,
    "dual_tariff": 0x94,
    "three_phase": 0x96,
}

MAGIC_BYTE = 0x82


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "iNode Energy Meter",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _build_mfr_data(device_type=0x90, flags=0x00, reserved=0x00, magic=MAGIC_BYTE,
                     total_pulses=0, average_power=0, battery_mv=0, battery_pct=0):
    """Build manufacturer_data for iNode Energy Meter."""
    return (
        bytes([device_type, flags, reserved, magic])
        + struct.pack("<I", total_pulses)
        + struct.pack("<H", average_power)
        + struct.pack("<H", battery_mv)
        + bytes([battery_pct])
    )


class TestINodeEnergyParser:
    def _registry_and_parser(self):
        registry = ParserRegistry()

        @register_parser(
            name="inode_energy",
            local_name_pattern=r"^iNode",
            description="iNode Energy Meter",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(INodeEnergyParser):
            pass

        return registry

    def test_match_by_local_name(self):
        """Should match advertisements with local_name starting with 'iNode'."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_no_match_wrong_name(self):
        """Should not match if local_name doesn't start with 'iNode'."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, local_name="SomeOtherDevice")
        assert len(registry.match(ad)) == 0

    def test_standard_device(self):
        """Parse standard energy meter (device_type=0x90)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(
            device_type=0x90,
            total_pulses=12345,
            average_power=450,
            battery_mv=3100,
            battery_pct=85,
        )
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "inode_energy"
        assert result.beacon_type == "inode_energy"
        assert result.device_class == "sensor"
        assert result.metadata["total_pulses"] == 12345
        assert result.metadata["average_power"] == 450
        assert result.metadata["battery_voltage"] == 3100
        assert result.metadata["battery_percent"] == 85
        assert result.metadata["device_type"] == "standard"

    def test_light_sensor_device(self):
        """Parse light sensor variant (device_type=0x92)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(device_type=0x92, total_pulses=100)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["device_type"] == "light_sensor"

    def test_dual_tariff_device(self):
        """Parse dual tariff variant (device_type=0x94)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(device_type=0x94, total_pulses=200)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["device_type"] == "dual_tariff"

    def test_three_phase_device(self):
        """Parse three-phase variant (device_type=0x96)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(device_type=0x96, total_pulses=300)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["device_type"] == "three_phase"

    def test_unknown_device_type(self):
        """Unknown device type byte should return None."""
        parser = INodeEnergyParser()
        mfr_data = _build_mfr_data(device_type=0xAA)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result is None

    def test_wrong_magic_byte(self):
        """Wrong magic byte at offset 3 should return None."""
        parser = INodeEnergyParser()
        mfr_data = _build_mfr_data(magic=0x99)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result is None

    def test_no_manufacturer_data(self):
        """No manufacturer data returns None."""
        parser = INodeEnergyParser()
        ad = _make_ad(manufacturer_data=None)
        result = parser.parse(ad)
        assert result is None

    def test_too_short_data(self):
        """Manufacturer data shorter than 13 bytes returns None."""
        parser = INodeEnergyParser()
        ad = _make_ad(manufacturer_data=b"\x90\x00\x00\x82\x01\x02")
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:inode_energy')[:16]."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:inode_energy".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex should be the full manufacturer_data hex."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(total_pulses=1, average_power=2, battery_mv=3, battery_pct=4)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.raw_payload_hex == mfr_data.hex()

    def test_large_pulse_count(self):
        """Should handle large uint32 pulse counts."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(total_pulses=4294967295)  # max uint32
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["total_pulses"] == 4294967295

    def test_zero_values(self):
        """Should handle all-zero sensor values."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["total_pulses"] == 0
        assert result.metadata["average_power"] == 0
        assert result.metadata["battery_voltage"] == 0
        assert result.metadata["battery_percent"] == 0

    def test_battery_percent_max(self):
        """Battery percent at 100%."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(battery_pct=100)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["battery_percent"] == 100
