"""Tests for Renpho/Etekcity smart scale plugin (detection only)."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.renpho import RenphoParser


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


class TestRenphoParser:
    def test_match_by_company_id(self):
        """Should match by company_id 0x06D0."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_by_local_name(self):
        """Should match by local_name 'QN-Scale'."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        ad = _make_ad(local_name="QN-Scale")
        assert len(registry.match(ad)) == 1

    def test_parse_result_device_class(self):
        """Should return ParseResult with device_class='scale'."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data, local_name="QN-Scale")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "scale"

    def test_parse_result_fields(self):
        """Should return correct parser_name and beacon_type."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data, local_name="QN-Scale")
        result = registry.match(ad)[0].parse(ad)
        assert result.parser_name == "renpho"
        assert result.beacon_type == "renpho"

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:QN-Scale')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(
            manufacturer_data=mfr_data,
            mac_address="11:22:33:44:55:66",
            local_name="QN-Scale",
        )
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:QN-Scale".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_match_wrong_company_id(self):
        """Should not match with wrong company_id and no matching name."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x9999) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data, local_name="OtherDevice")
        assert len(registry.match(ad)) == 0
