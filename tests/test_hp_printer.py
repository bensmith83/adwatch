"""Tests for HP Printer BLE presence plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.hp_printer import HPPrinterParser, HP_COMPANY_ID, HP_UUIDS


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="hp_printer",
        company_id=HP_COMPANY_ID,
        service_uuid=HP_UUIDS,
        description="HP Printers",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(HPPrinterParser):
        pass

    return registry


class TestHPPrinterParser:
    def test_match_by_company_id(self):
        """Should match by company_id 0x0434."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x0434) + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_by_service_uuid_fdf7(self):
        """Should match by service_uuid fdf7."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fdf7"])
        assert len(registry.match(ad)) == 1

    def test_match_by_service_uuid_fe77(self):
        """Should match by service_uuid fe77."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fe77"])
        assert len(registry.match(ad)) == 1

    def test_match_by_service_uuid_fe78(self):
        """Should match by service_uuid fe78."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fe78"])
        assert len(registry.match(ad)) == 1

    def test_parses_printer_model_from_local_name(self):
        """Printer model extracted from local_name."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x0434) + b"\x01"
        ad = _make_ad(
            manufacturer_data=mfr_data,
            local_name="HP LaserJet Pro M404dn",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["printer_model"] == "HP LaserJet Pro M404dn"

    def test_device_class_is_printer(self):
        """Device class should be 'printer'."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x0434) + b"\x01"
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "printer"

    def test_returns_none_when_no_match(self):
        """Should return None when no matching signal."""
        registry = _make_registry()
        # Different company ID, no matching UUIDs
        mfr_data = struct.pack("<H", 0x9999) + b"\x01"
        ad = _make_ad(manufacturer_data=mfr_data)
        matches = registry.match(ad)
        if matches:
            result = matches[0].parse(ad)
            assert result is None
        # If registry doesn't match, that's also correct

    def test_works_with_just_service_uuid_no_mfr_data(self):
        """Should parse successfully with only service UUID, no manufacturer data."""
        registry = _make_registry()
        ad = _make_ad(
            service_data={"fdf7": b"\x01\x02"},
            service_uuids=["fdf7"],
            local_name="HP ENVY 6055e",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["printer_model"] == "HP ENVY 6055e"
        assert result.raw_payload_hex == ""

    def test_identity_hash_based_on_mac(self):
        """Identity hash: SHA256('{mac}:hp_printer')[:16]."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x0434) + b"\x01"
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:hp_printer".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected
