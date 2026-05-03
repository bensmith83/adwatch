"""Tests for ResMed CPAP BLE advertisement parser."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.resmed import ResmedParser, RESMED_COMPANY_ID, RESMED_SERVICE_UUID


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="resmed",
        company_id=RESMED_COMPANY_ID,
        service_uuid=RESMED_SERVICE_UUID,
        local_name_pattern=r"^ResMed\s",
        description="ResMed CPAP/sleep device advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ResmedParser):
        pass

    return registry


def _make_raw(
    local_name=None,
    manufacturer_data=None,
    service_uuids=None,
    service_data=None,
    mac="AA:BB:CC:DD:EE:FF",
):
    return RawAdvertisement(
        timestamp="2026-04-05T16:31:41Z",
        mac_address=mac,
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
    )


class TestResmedParser:
    def test_parses_by_local_name_and_service_uuid(self):
        parser = ResmedParser()
        raw = _make_raw(
            local_name="ResMed 111682",
            manufacturer_data=bytes.fromhex("8d0300"),
            service_uuids=["0000fd56-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "resmed"
        assert result.beacon_type == "resmed"
        assert result.device_class == "cpap"
        assert result.metadata["device_number"] == "111682"

    def test_parses_by_service_uuid_only(self):
        parser = ResmedParser()
        raw = _make_raw(
            manufacturer_data=bytes.fromhex("8d0300"),
            service_uuids=["0000fd56-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "resmed"

    def test_parses_by_local_name_only(self):
        parser = ResmedParser()
        raw = _make_raw(local_name="ResMed 828156")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_number"] == "828156"

    def test_extracts_company_id(self):
        parser = ResmedParser()
        raw = _make_raw(
            local_name="ResMed 111682",
            manufacturer_data=bytes.fromhex("8d0300"),
            service_uuids=["0000fd56-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(raw)
        assert result.metadata["company_id"] == "0x038d"

    def test_rejects_unrelated_device(self):
        parser = ResmedParser()
        raw = _make_raw(
            local_name="SomeOtherDevice",
            manufacturer_data=bytes.fromhex("ff0001"),
        )
        result = parser.parse(raw)
        assert result is None

    def test_identifier_hash_stable(self):
        parser = ResmedParser()
        raw = _make_raw(
            local_name="ResMed 111682",
            manufacturer_data=bytes.fromhex("8d0300"),
            service_uuids=["0000fd56-0000-1000-8000-00805f9b34fb"],
        )
        r1 = parser.parse(raw)
        r2 = parser.parse(raw)
        assert r1.identifier_hash == r2.identifier_hash
        assert len(r1.identifier_hash) == 16

    def test_different_devices_different_hashes(self):
        parser = ResmedParser()
        raw1 = _make_raw(local_name="ResMed 111682", mac="AA:BB:CC:DD:EE:01")
        raw2 = _make_raw(local_name="ResMed 828156", mac="AA:BB:CC:DD:EE:02")
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestResmedRegistration:
    def test_matches_service_uuid(self):
        registry = _make_registry()
        raw = _make_raw(
            manufacturer_data=bytes.fromhex("8d0300"),
            service_uuids=["0000fd56-0000-1000-8000-00805f9b34fb"],
        )
        matches = registry.match(raw)
        assert len(matches) >= 1

    def test_matches_local_name(self):
        registry = _make_registry()
        raw = _make_raw(local_name="ResMed 111682")
        matches = registry.match(raw)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        parser = ResmedParser()
        raw = _make_raw(local_name="SomeDevice")
        result = parser.parse(raw)
        assert result is None


class TestResmedAirFamily:
    """AirMini / AS11 / AirCurve 11 (per myAir report)."""

    def test_airmini_serial_extracted(self):
        parser = ResmedParser()
        raw = _make_raw(local_name="AirMini-1234567890")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["product_family"] == "AirMini"
        assert result.metadata["serial"] == "1234567890"

    def test_as11_family_match(self):
        parser = ResmedParser()
        raw = _make_raw(local_name="AS11-ABCDEFGHIJ")
        result = parser.parse(raw)
        assert result.metadata["product_family"] == "AS11"
        assert result.metadata["serial"] == "ABCDEFGHIJ"

    def test_aircurve_family_match(self):
        parser = ResmedParser()
        raw = _make_raw(local_name="AirCurve-XYZ123ABC456")
        result = parser.parse(raw)
        assert result.metadata["product_family"] == "AirCurve"

    def test_identity_uses_serial(self):
        import hashlib
        parser = ResmedParser()
        raw = _make_raw(local_name="AirMini-1234567890",
                        mac="11:22:33:44:55:66")
        result = parser.parse(raw)
        expected = hashlib.sha256(b"resmed:1234567890").hexdigest()[:16]
        assert result.identifier_hash == expected


class TestResmedNightOwl:
    def test_nightowl_uuid_match(self):
        from adwatch.plugins.resmed import NIGHTOWL_SERVICE_UUID
        parser = ResmedParser()
        raw = _make_raw(service_uuids=[NIGHTOWL_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["product_family"] == "NightOwl"
        assert result.device_class == "sleep_test"

    def test_nightowl_name_match(self):
        parser = ResmedParser()
        raw = _make_raw(local_name="NightOwl-123")
        result = parser.parse(raw)
        assert result.metadata["product_family"] == "NightOwl"
        assert result.device_class == "sleep_test"


class TestResmedPOC:
    def test_poc_uuid_match(self):
        from adwatch.plugins.resmed import POC_SERVICE_UUID
        parser = ResmedParser()
        raw = _make_raw(service_uuids=[POC_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["product_family"] == "POC"
        assert result.device_class == "oxygen_concentrator"
