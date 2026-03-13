"""Tests for Victron Energy Instant Readout plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.victron_energy import VictronEnergyParser


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _build_victron_mfr_data(prefix=0x10, reserved=0x00, model_id=0x1234,
                             record_type=0x01, iv=0x0001, key_byte=0xAA,
                             encrypted=b"\x00" * 8):
    """Build Victron manufacturer data: company_id(2) + payload."""
    data = struct.pack("<H", 0x02E1)  # company_id LE
    data += bytes([prefix, reserved])
    data += struct.pack("<H", model_id)
    data += bytes([record_type])
    data += struct.pack("<H", iv)
    data += bytes([key_byte])
    data += encrypted
    return data


class TestVictronEnergyParser:
    def test_company_id_and_prefix(self):
        """Should match company ID 0x02E1 with prefix byte 0x10."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        parsers = registry.match(ad)
        assert len(parsers) == 1
        result = parsers[0].parse(ad)
        assert result is not None
        assert result.parser_name == "victron_energy"
        assert result.beacon_type == "victron_energy"

    def test_model_id_extraction(self):
        """Model ID should be extracted as uint16 LE at offset 2-3 of payload."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(model_id=0xA389)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model_id"] == 0xA389

    def test_record_type_solar_charger(self):
        """Record type 0x01 = Solar Charger."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(record_type=0x01)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["device_type"] == "Solar Charger"

    def test_record_type_battery_monitor(self):
        """Record type 0x02 = Battery Monitor."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(record_type=0x02)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["device_type"] == "Battery Monitor"

    def test_record_type_inverter(self):
        """Record type 0x03 = Inverter."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(record_type=0x03)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["device_type"] == "Inverter"

    def test_iv_data_counter_extraction(self):
        """IV/data counter should be extracted as uint16 LE."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(iv=0x1234)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["data_counter"] == 0x1234

    def test_wrong_prefix_returns_none(self):
        """Wrong prefix byte (not 0x10) should return None."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(prefix=0x20)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:{model_id}')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data(model_id=0xA389)
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:41865".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class_is_energy(self):
        """Device class should be 'energy'."""
        registry = ParserRegistry()

        @register_parser(
            name="victron_energy", company_id=0x02E1,
            description="Victron Energy", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(VictronEnergyParser):
            pass

        mfr_data = _build_victron_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "energy"
