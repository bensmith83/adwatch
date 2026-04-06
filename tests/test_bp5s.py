"""Tests for iHealth/Andon BP5S blood pressure monitor BLE advertisement parser."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.bp5s_blood_pressure import (
    Bp5sParser,
    BP5S_SERVICE_UUID,
    BP5S_COMPANY_ID,
)


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="bp5s",
        company_id=BP5S_COMPANY_ID,
        service_uuid=BP5S_SERVICE_UUID,
        local_name_pattern=r"^BP5S\s",
        description="iHealth/Andon BP5S blood pressure monitor advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(Bp5sParser):
        pass

    return registry


def _make_raw(
    local_name=None,
    manufacturer_data=None,
    service_uuids=None,
    mac="AA:BB:CC:DD:EE:FF",
):
    return RawAdvertisement(
        timestamp="2026-04-05T17:45:21Z",
        mac_address=mac,
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=None,
        service_uuids=service_uuids or [],
        local_name=local_name,
    )


BP5S_UUID = "636f6d2e-6a69-7561-6e2e-425056323500"
BP5S_MFR_DATA = bytes.fromhex("590000000000004d323c1b68")


class TestBp5sParser:
    def test_parses_by_local_name_and_uuid(self):
        parser = Bp5sParser()
        raw = _make_raw(
            local_name="BP5S 11070",
            manufacturer_data=BP5S_MFR_DATA,
            service_uuids=[BP5S_UUID],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "bp5s"
        assert result.beacon_type == "bp5s"
        assert result.device_class == "blood_pressure_monitor"

    def test_extracts_serial_number(self):
        parser = Bp5sParser()
        raw = _make_raw(
            local_name="BP5S 11070",
            service_uuids=[BP5S_UUID],
        )
        result = parser.parse(raw)
        assert result.metadata["serial_number"] == "11070"
        assert result.metadata["device_name"] == "BP5S 11070"

    def test_parses_by_service_uuid_only(self):
        parser = Bp5sParser()
        raw = _make_raw(service_uuids=[BP5S_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "bp5s"

    def test_parses_by_local_name_only(self):
        parser = Bp5sParser()
        raw = _make_raw(local_name="BP5S 11070")
        result = parser.parse(raw)
        assert result is not None

    def test_rejects_unrelated_device(self):
        parser = Bp5sParser()
        raw = _make_raw(
            local_name="SomeDevice",
            service_uuids=["0000feaf-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(raw)
        assert result is None

    def test_identifier_hash_stable(self):
        parser = Bp5sParser()
        raw = _make_raw(
            local_name="BP5S 11070",
            service_uuids=[BP5S_UUID],
        )
        r1 = parser.parse(raw)
        r2 = parser.parse(raw)
        assert r1.identifier_hash == r2.identifier_hash
        assert len(r1.identifier_hash) == 16

    def test_extracts_company_id(self):
        parser = Bp5sParser()
        raw = _make_raw(
            local_name="BP5S 11070",
            manufacturer_data=BP5S_MFR_DATA,
            service_uuids=[BP5S_UUID],
        )
        result = parser.parse(raw)
        assert result.metadata["company_id"] == "0x0059"


class TestBp5sRegistration:
    def test_matches_service_uuid(self):
        registry = _make_registry()
        raw = _make_raw(service_uuids=[BP5S_UUID])
        matches = registry.match(raw)
        assert len(matches) >= 1

    def test_matches_local_name(self):
        registry = _make_registry()
        raw = _make_raw(local_name="BP5S 11070")
        matches = registry.match(raw)
        assert len(matches) >= 1
