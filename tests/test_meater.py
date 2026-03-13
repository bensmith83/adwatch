"""Tests for MEATER wireless meat thermometer plugin (detection only)."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.meater import MEATERParser


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


def _build_meater_mfr_data(payload=b"\x01\x02\x03\x04"):
    """Build MEATER manufacturer data with company ID 0x037B."""
    import struct
    return struct.pack("<H", 0x037B) + payload


class TestMEATERParser:
    def test_match_by_company_id(self):
        """Should match by company_id 0x037B."""
        registry = ParserRegistry()

        @register_parser(
            name="meater", company_id=0x037B, local_name_pattern=r"^MEATER",
            description="MEATER", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MEATERParser):
            pass

        mfr_data = _build_meater_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_by_local_name(self):
        """Should match by local_name 'MEATER'."""
        registry = ParserRegistry()

        @register_parser(
            name="meater", company_id=0x037B, local_name_pattern=r"^MEATER",
            description="MEATER", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MEATERParser):
            pass

        ad = _make_ad(local_name="MEATER")
        assert len(registry.match(ad)) == 1

    def test_parse_result_fields(self):
        """Should return ParseResult with device_class='sensor', beacon_type='meater'."""
        registry = ParserRegistry()

        @register_parser(
            name="meater", company_id=0x037B, local_name_pattern=r"^MEATER",
            description="MEATER", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MEATERParser):
            pass

        mfr_data = _build_meater_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, local_name="MEATER")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.parser_name == "meater"
        assert result.beacon_type == "meater"
        assert result.device_class == "sensor"

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:MEATER')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="meater", company_id=0x037B, local_name_pattern=r"^MEATER",
            description="MEATER", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MEATERParser):
            pass

        mfr_data = _build_meater_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:MEATER".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_match_wrong_company_id(self):
        """Should not match with wrong company_id."""
        registry = ParserRegistry()

        @register_parser(
            name="meater", company_id=0x037B,
            description="MEATER", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(MEATERParser):
            pass

        import struct
        mfr_data = struct.pack("<H", 0x9999) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 0
