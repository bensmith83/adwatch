"""Tests for Molekule air purifier BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.molekule import MolekuleParser, MOLEKULE_SERVICE_UUID, MOLEKULE_NAME_RE


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
        name="molekule",
        service_uuid=MOLEKULE_SERVICE_UUID,
        local_name_pattern=r"^MOLEKULE_",
        description="Molekule air purifier advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(MolekuleParser):
        pass

    return registry


class TestMolekuleMatching:
    def test_matches_service_uuid(self):
        """Matches on Molekule service UUID FE4F."""
        registry = _make_registry()
        ad = _make_ad(
            service_uuids=["0000fe4f-0000-1000-8000-00805f9b34fb"],
            local_name="MOLEKULE_0868",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name(self):
        """Matches on MOLEKULE_ prefix."""
        registry = _make_registry()
        ad = _make_ad(local_name="MOLEKULE_0868")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_unrelated(self):
        """Does not match unrelated devices."""
        parser = MolekuleParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None


class TestMolekuleParsing:
    def test_parse_basic(self):
        """Parses Molekule air purifier advertisement."""
        parser = MolekuleParser()
        mfr = bytes.fromhex("4d48314d2d5348413139303431352d303030383638e4")
        ad = _make_ad(
            local_name="MOLEKULE_0868",
            manufacturer_data=mfr,
            service_uuids=["0000fe4f-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "molekule"
        assert result.beacon_type == "molekule"
        assert result.device_class == "air_purifier"

    def test_serial_extracted_from_mfr_data(self):
        """Serial info extracted from ASCII manufacturer data."""
        parser = MolekuleParser()
        # MH1M-SHA190415-000868 + trailing byte
        mfr = bytes.fromhex("4d48314d2d5348413139303431352d303030383638e4")
        ad = _make_ad(
            local_name="MOLEKULE_0868",
            manufacturer_data=mfr,
            service_uuids=["0000fe4f-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result.metadata["serial_info"] == "MH1M-SHA190415-000868"

    def test_device_id_from_name(self):
        """Device ID extracted from local name suffix."""
        parser = MolekuleParser()
        ad = _make_ad(
            local_name="MOLEKULE_0868",
            service_uuids=["0000fe4f-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "0868"

    def test_identity_hash(self):
        """Identity hash is SHA256('molekule:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = MolekuleParser()
        ad = _make_ad(
            local_name="MOLEKULE_0868",
            service_uuids=["0000fe4f-0000-1000-8000-00805f9b34fb"],
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"molekule:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex contains manufacturer data."""
        parser = MolekuleParser()
        mfr = bytes.fromhex("4d48314d2d5348413139303431352d303030383638e4")
        ad = _make_ad(
            local_name="MOLEKULE_0868",
            manufacturer_data=mfr,
        )
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr.hex()

    def test_parse_without_mfr_data(self):
        """Parses with name + UUID even without manufacturer data."""
        parser = MolekuleParser()
        ad = _make_ad(
            local_name="MOLEKULE_0868",
            service_uuids=["0000fe4f-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert "serial_info" not in result.metadata

    def test_no_match_without_name_or_uuid(self):
        """Returns None without matching name or UUID."""
        parser = MolekuleParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
