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


class TestVictronReportEnrichment:
    """Fields verified against reports/victronenergy-victronconnect_passive.md.

    Payload offsets are relative to the value stored under the 0x02E1
    manufacturer key, i.e. RawAdvertisement.manufacturer_payload.
    """

    def _parse(self, **kw):
        ad = _make_ad(manufacturer_data=_build_victron_mfr_data(**kw))
        return VictronEnergyParser().parse(ad)

    def test_record_format_mode_low_nibble_of_byte1(self):
        # 0x05 → mode 5, no flag bits
        result = self._parse(reserved=0x05)
        assert result.metadata["readout_flags"] == 0x05
        assert result.metadata["record_format_mode"] == 0x05
        assert result.metadata["flag_bit6"] is False
        assert result.metadata["flag_bit7"] is False

    def test_readout_flag_bits_6_and_7(self):
        result = self._parse(reserved=0xC3)
        assert result.metadata["record_format_mode"] == 0x03
        assert result.metadata["flag_bit6"] is True
        assert result.metadata["flag_bit7"] is True

    def test_key_check_byte_exposed(self):
        """Byte 7 is advertisement_key[0] in the clear (key-rotation canary)."""
        result = self._parse(key_byte=0x5C)
        assert result.metadata["key_check_byte"] == 0x5C

    def test_encrypted_payload_reported(self):
        """Bytes 8..end are AES-128-CTR ciphertext; surface them verbatim."""
        cipher = bytes.fromhex("deadbeefcafe0102")
        result = self._parse(encrypted=cipher)
        assert result.metadata["encrypted"] is True
        assert result.metadata["encrypted_len"] == len(cipher)
        assert result.metadata["encrypted_payload_hex"] == cipher.hex()

    def test_no_ciphertext_when_payload_stops_at_key_byte(self):
        result = self._parse(encrypted=b"")
        assert result.metadata["encrypted_len"] == 0
        assert "encrypted_payload_hex" not in result.metadata

    def test_iv_alias_matches_data_counter(self):
        """Report calls bytes 5-6 the `iv`; the plugin already had data_counter."""
        result = self._parse(iv=0xBEEF)
        assert result.metadata["data_counter"] == 0xBEEF
        assert result.metadata["iv"] == 0xBEEF

    def test_header_only_four_byte_payload_still_matches(self):
        """The app's gate is company==0x02E1 && byte0==0x10 && len>=4."""
        mfr = struct.pack("<H", 0x02E1) + bytes([0x10, 0x00]) + struct.pack("<H", 0xA389)
        result = VictronEnergyParser().parse(_make_ad(manufacturer_data=mfr))
        assert result is not None
        assert result.metadata["model_id"] == 0xA389
        assert "record_type" not in result.metadata
        assert result.metadata["encrypted"] is False

    def test_three_byte_payload_rejected(self):
        mfr = struct.pack("<H", 0x02E1) + bytes([0x10, 0x00, 0x89])
        assert VictronEnergyParser().parse(_make_ad(manufacturer_data=mfr)) is None

    def test_wrong_company_id_rejected(self):
        mfr = struct.pack("<H", 0x004C) + bytes([0x10, 0x00]) + struct.pack("<H", 1)
        assert VictronEnergyParser().parse(_make_ad(manufacturer_data=mfr)) is None

    @pytest.mark.parametrize("code,name", [
        (0x01, "Solar Charger"),
        (0x02, "Battery Monitor"),
        (0x03, "Inverter"),
        (0x04, "DC/DC Converter"),
        (0x05, "SmartLithium"),
        (0x06, "Inverter RS"),
        (0x07, "GX Device"),
        (0x08, "AC Charger"),
        (0x09, "Smart Battery Protect"),
        (0x0A, "Lynx Smart BMS"),
        (0x0B, "Multi RS"),
        (0x0C, "VE.Bus"),
        (0x0D, "DC Energy Meter"),
        (0x0F, "Orion XS"),
    ])
    def test_record_type_table(self, code, name):
        result = self._parse(record_type=code)
        assert result.metadata["device_type"] == name

    def test_unknown_record_type(self):
        result = self._parse(record_type=0x7E)
        assert result.metadata["device_type"] == "Unknown"
