"""Tests for Hunter Douglas PowerView Gen 3 BLE advertisement parser."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.hunter_douglas_powerview import (
    HunterDouglasPowerViewParser,
    HUNTER_DOUGLAS_COMPANY_ID,
    HUNTER_DOUGLAS_SERVICE_UUID,
)


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="hunter_douglas_powerview",
        company_id=HUNTER_DOUGLAS_COMPANY_ID,
        service_uuid=HUNTER_DOUGLAS_SERVICE_UUID,
        local_name_pattern=r"^[A-Z]{3}:[0-9A-Fa-f]{4}$",
        description="Hunter Douglas PowerView Gen 3 motorized shade advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(HunterDouglasPowerViewParser):
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
        timestamp="2026-04-05T16:26:48Z",
        mac_address=mac,
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
    )


# Observed SIL data: 19088a6c170000000000c2
# Observed DUE data: 1908116009400b000000c2

SIL_MFR_DATA = bytes.fromhex("19088a6c170000000000c2")
DUE_MFR_DATA = bytes.fromhex("1908116009400b000000c2")
FDC1_UUID = "0000fdc1-0000-1000-8000-00805f9b34fb"


class TestHunterDouglasParser:
    def test_parses_silhouette_shade(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            local_name="SIL:4914",
            manufacturer_data=SIL_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "hunter_douglas_powerview"
        assert result.beacon_type == "hunter_douglas"
        assert result.device_class == "motorized_shade"

    def test_parses_duette_shade(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            local_name="DUE:1568",
            manufacturer_data=DUE_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.device_class == "motorized_shade"

    def test_extracts_silhouette_metadata(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            local_name="SIL:4914",
            manufacturer_data=SIL_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        result = parser.parse(raw)
        m = result.metadata
        assert m["product_line"] == "Silhouette"
        assert m["device_id"] == "4914"
        assert m["home_id"] == "0x6c8a"
        assert m["type_id"] == 23
        assert m["position_pct"] == 0.0
        assert m["tilt"] == 0
        assert m["battery"] == "100%"
        assert m["motion"] == "idle"

    def test_extracts_duette_metadata(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            local_name="DUE:1568",
            manufacturer_data=DUE_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        result = parser.parse(raw)
        m = result.metadata
        assert m["product_line"] == "Duette"
        assert m["device_id"] == "1568"
        assert m["home_id"] == "0x6011"
        assert m["type_id"] == 9
        assert m["battery"] == "100%"
        # position1 raw bytes at offset 3-4 (after company ID removal): 40 0b
        # LE uint16 = 0x0b40 = 2880, bits[15:2] = 2880 >> 2 = 720, /10 = 72.0%
        assert m["position_pct"] == 72.0

    def test_parses_by_company_id_only(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            manufacturer_data=SIL_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "hunter_douglas_powerview"

    def test_rejects_unrelated_device(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            local_name="SomeDevice",
            manufacturer_data=bytes.fromhex("ff0001020304050607080a"),
        )
        result = parser.parse(raw)
        assert result is None

    def test_identifier_hash_stable(self):
        parser = HunterDouglasPowerViewParser()
        raw = _make_raw(
            local_name="SIL:4914",
            manufacturer_data=SIL_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        r1 = parser.parse(raw)
        r2 = parser.parse(raw)
        assert r1.identifier_hash == r2.identifier_hash
        assert len(r1.identifier_hash) == 16

    def test_different_shades_different_hashes(self):
        parser = HunterDouglasPowerViewParser()
        raw1 = _make_raw(
            local_name="SIL:4914",
            manufacturer_data=SIL_MFR_DATA,
            mac="AA:BB:CC:DD:EE:01",
        )
        raw2 = _make_raw(
            local_name="SIL:E869",
            manufacturer_data=SIL_MFR_DATA,
            mac="AA:BB:CC:DD:EE:02",
        )
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_motion_flags(self):
        parser = HunterDouglasPowerViewParser()
        # Modify position1 to have motion flag = 1 (closing)
        data = bytearray(SIL_MFR_DATA)
        data[5] = 0x01  # bits [1:0] = 01 = closing
        raw = _make_raw(
            local_name="SIL:4914",
            manufacturer_data=bytes(data),
            service_uuids=[FDC1_UUID],
        )
        result = parser.parse(raw)
        assert result.metadata["motion"] == "closing"

    def test_battery_levels(self):
        parser = HunterDouglasPowerViewParser()
        for status_byte, expected in [(0xC2, "100%"), (0x82, "50%"), (0x42, "20%"), (0x02, "0%")]:
            data = bytearray(SIL_MFR_DATA)
            data[10] = status_byte
            raw = _make_raw(
                local_name="SIL:4914",
                manufacturer_data=bytes(data),
                service_uuids=[FDC1_UUID],
            )
            result = parser.parse(raw)
            assert result.metadata["battery"] == expected, f"status_byte={status_byte:#x}"


class TestHunterDouglasRegistration:
    def test_matches_company_id(self):
        registry = _make_registry()
        raw = _make_raw(
            manufacturer_data=SIL_MFR_DATA,
            service_uuids=[FDC1_UUID],
        )
        matches = registry.match(raw)
        assert len(matches) >= 1

    def test_matches_local_name(self):
        registry = _make_registry()
        raw = _make_raw(local_name="SIL:4914")
        matches = registry.match(raw)
        assert len(matches) >= 1
