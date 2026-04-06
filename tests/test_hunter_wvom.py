"""Tests for Hunter Industries WVOM BLE advertisement parser."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.hunter_wvom import HunterWvomParser, WVOM_SERVICE_UUID


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="hunter_wvom",
        service_uuid=WVOM_SERVICE_UUID,
        local_name_pattern=r"^WVOM-",
        description="Hunter Industries WVOM irrigation controller advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(HunterWvomParser):
        pass

    return registry


def _make_raw(
    local_name=None,
    manufacturer_data=None,
    service_uuids=None,
    mac="AA:BB:CC:DD:EE:FF",
):
    return RawAdvertisement(
        timestamp="2026-04-05T16:27:03Z",
        mac_address=mac,
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=None,
        service_uuids=service_uuids or [],
        local_name=local_name,
    )


WVOM_UUID = "0ed3e3d3-8cd8-4f29-8fec-a7d3a2c5443e"


class TestHunterWvomParser:
    def test_parses_by_local_name(self):
        parser = HunterWvomParser()
        raw = _make_raw(
            local_name="WVOM-147516",
            service_uuids=[WVOM_UUID],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "hunter_wvom"
        assert result.beacon_type == "hunter_wvom"
        assert result.device_class == "irrigation"

    def test_extracts_serial_number(self):
        parser = HunterWvomParser()
        raw = _make_raw(
            local_name="WVOM-147516",
            service_uuids=[WVOM_UUID],
        )
        result = parser.parse(raw)
        assert result.metadata["serial_number"] == "147516"
        assert result.metadata["device_name"] == "WVOM-147516"

    def test_parses_by_service_uuid_only(self):
        parser = HunterWvomParser()
        raw = _make_raw(service_uuids=[WVOM_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "hunter_wvom"

    def test_rejects_unrelated_device(self):
        parser = HunterWvomParser()
        raw = _make_raw(
            local_name="SomeDevice",
            service_uuids=["0000feaf-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(raw)
        assert result is None

    def test_identifier_hash_stable(self):
        parser = HunterWvomParser()
        raw = _make_raw(
            local_name="WVOM-147516",
            service_uuids=[WVOM_UUID],
        )
        r1 = parser.parse(raw)
        r2 = parser.parse(raw)
        assert r1.identifier_hash == r2.identifier_hash
        assert len(r1.identifier_hash) == 16

    def test_different_devices_different_hashes(self):
        parser = HunterWvomParser()
        raw1 = _make_raw(local_name="WVOM-147516", mac="AA:BB:CC:DD:EE:01")
        raw2 = _make_raw(local_name="WVOM-999999", mac="AA:BB:CC:DD:EE:02")
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestHunterWvomRegistration:
    def test_matches_service_uuid(self):
        registry = _make_registry()
        raw = _make_raw(service_uuids=[WVOM_UUID])
        matches = registry.match(raw)
        assert len(matches) >= 1

    def test_matches_local_name(self):
        registry = _make_registry()
        raw = _make_raw(local_name="WVOM-147516")
        matches = registry.match(raw)
        assert len(matches) >= 1
