"""Tests for Airthings Wave air quality monitor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.airthings import AirthingsParser


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


def _build_airthings_mfr_data(serial_number):
    """Build Airthings mfr data: company_id(2) + serial(4 LE)."""
    data = struct.pack("<H", 0x0334)  # company_id
    data += struct.pack("<I", serial_number)
    return data


class TestAirthingsParser:
    def test_company_id_match(self):
        """Should match company ID 0x0334."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(2900123456)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_serial_number_extraction(self):
        """Serial number should be extracted as uint32 LE from payload bytes 0-3."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        serial = 2930567890
        mfr_data = _build_airthings_mfr_data(serial)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["serial_number"] == serial

    def test_model_wave_gen1(self):
        """Serial prefix 2900 → Wave Gen 1."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(2900100000)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["model"] == "Wave Gen 1"

    def test_model_wave_mini(self):
        """Serial prefix 2920 → Wave Mini."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(2920100000)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["model"] == "Wave Mini"

    def test_model_wave_plus(self):
        """Serial prefix 2930 → Wave Plus."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(2930100000)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["model"] == "Wave Plus"

    def test_model_wave_radon(self):
        """Serial prefix 2950 → Wave Radon Gen 2."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(2950100000)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["model"] == "Wave Radon Gen 2"

    def test_unknown_serial_prefix(self):
        """Unknown serial prefix → 'Unknown' model."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(3999100000)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["model"] == "Unknown"

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:{serial_number}')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        serial = 2930567890
        mfr_data = _build_airthings_mfr_data(serial)
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256(f"11:22:33:44:55:66:{serial}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_too_short_payload_returns_none(self):
        """Payload shorter than 4 bytes should return None."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = struct.pack("<H", 0x0334) + b"\x01\x02"  # only 2 payload bytes
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_device_class(self):
        """Device class should be 'sensor'."""
        registry = ParserRegistry()

        @register_parser(
            name="airthings", company_id=0x0334,
            description="Airthings", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AirthingsParser):
            pass

        mfr_data = _build_airthings_mfr_data(2900100000)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "sensor"
