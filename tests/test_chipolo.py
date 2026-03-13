"""Tests for Chipolo tracker tag plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.chipolo import ChipoloParser


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


class TestChipoloParser:
    def test_match_by_company_id(self):
        """Should match by company_id 0x08C3."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        mfr_data = struct.pack("<H", 0x08C3) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_by_service_uuid_fe33(self):
        """Should match by service_uuid fe33 with service data."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        ad = _make_ad(service_data={"fe33": b"\x03"}, service_uuids=["fe33"])
        assert len(registry.match(ad)) == 1

    def test_color_code_extraction(self):
        """Color code should be extracted from service data byte 0."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        ad = _make_ad(
            service_data={"fe33": b"\x04"},
            service_uuids=["fe33"],
            manufacturer_data=struct.pack("<H", 0x08C3) + b"\x01",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["color_code"] == 4

    def test_color_lookup_gray(self):
        """Color code 0 → Gray."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        ad = _make_ad(
            service_data={"fe33": b"\x00"},
            manufacturer_data=struct.pack("<H", 0x08C3) + b"\x01",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["color"] == "Gray"

    def test_color_lookup_white(self):
        """Color code 1 → White."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        ad = _make_ad(
            service_data={"fe33": b"\x01"},
            manufacturer_data=struct.pack("<H", 0x08C3) + b"\x01",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["color"] == "White"

    def test_color_lookup_pink(self):
        """Color code 9 → Pink."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        ad = _make_ad(
            service_data={"fe33": b"\x09"},
            manufacturer_data=struct.pack("<H", 0x08C3) + b"\x01",
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["color"] == "Pink"

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:chipolo')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        mfr_data = struct.pack("<H", 0x08C3) + b"\x01"
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:chipolo".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self):
        """Device class should be 'tracker'."""
        registry = ParserRegistry()

        @register_parser(
            name="chipolo", company_id=0x08C3, service_uuid="fe33",
            description="Chipolo", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(ChipoloParser):
            pass

        mfr_data = struct.pack("<H", 0x08C3) + b"\x01"
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "tracker"
