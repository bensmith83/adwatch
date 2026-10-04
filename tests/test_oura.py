"""Tests for Oura Ring plugin."""

import struct
import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.oura import (
    OuraParser, OURA_COMPANY_ID,
    OURA_DATA_SERVICE_UUID, OURA_CHARGER_SERVICE_UUID,
    CYPRESS_BOOTLOADER_SERVICE_UUID, GENERATIONS,
)


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


def _register(registry):
    @register_parser(
        name="oura",
        company_id=OURA_COMPANY_ID,
        service_uuid=(OURA_DATA_SERVICE_UUID, OURA_CHARGER_SERVICE_UUID),
        description="Oura",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(OuraParser):
        pass
    return _P


def _mfr(payload: bytes) -> bytes:
    return struct.pack("<H", OURA_COMPANY_ID) + payload


class TestOuraMatching:
    def test_matches_data_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[OURA_DATA_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_charger_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[OURA_CHARGER_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(bytes(4)))
        assert len(registry.match(ad)) == 1


class TestOuraParsing:
    def _parse(self, **kw):
        return OuraParser().parse(_make_ad(**kw))

    def test_charger_kind(self):
        result = self._parse(service_uuids=[OURA_CHARGER_SERVICE_UUID])
        assert result.metadata["device_kind"] == "charger_puck"

    def test_cypress_bootloader_uuid_alone_is_not_oura(self):
        """00060000-f8ce-11e4-abf4-0002a5d5c51b is Cypress's generic
        bootloader (OTA/DFU) service, shared by any PSoC/Cypress product —
        too generic to identify an Oura ring."""
        assert self._parse(service_uuids=[CYPRESS_BOOTLOADER_SERVICE_UUID]) is None

    def test_cypress_bootloader_uuid_not_registered(self):
        from adwatch.registry import _default_registry
        entry = [e for e in _default_registry.get_entries() if e["name"] == "oura"][0]
        uuids = [u.lower() for u in entry["service_uuid"]]
        assert CYPRESS_BOOTLOADER_SERVICE_UUID not in uuids

    # Name-matched corpus captures (NearSight telemetry, 2026-09-29):
    #   b2 02 | 04 40 5a 06  "Oura Ring Gen3"
    #   b2 02 | 04 60 5b 01  "Oura Ring 4"
    #   b2 02 | 04 70 1b 01  "Oura Ring 5"
    @pytest.mark.parametrize("hexframe,name,gen_byte,generation,rev", [
        ("b20204405a06", "Oura Ring Gen3", 0x40, "Gen 3", 0x065A),
        ("b20204605b01", "Oura Ring 4", 0x60, "Ring 4", 0x015B),
        ("b20204701b01", "Oura Ring 5", 0x70, "Ring 5", 0x011B),
    ])
    def test_corpus_generation_byte(self, hexframe, name, gen_byte, generation, rev):
        result = self._parse(manufacturer_data=bytes.fromhex(hexframe), local_name=name)
        md = result.metadata
        assert md["frame_type"] == 0x04
        assert md["generation_byte"] == gen_byte
        assert md["generation"] == generation
        assert md["fw_revision"] == rev
        for stale in ("hardware_type", "mode", "color_code", "design_code", "i_nibble"):
            assert stale not in md

    def test_unknown_generation_byte_raw(self):
        result = self._parse(manufacturer_data=bytes.fromhex("b20204621801"))
        assert result.metadata["generation_byte"] == 0x62
        assert "generation" not in result.metadata

    def test_generation_table(self):
        assert GENERATIONS == {0x40: "Gen 3", 0x60: "Ring 4", 0x70: "Ring 5"}

    def test_returns_none_unrelated(self):
        assert self._parse(local_name="Other") is None

    def test_parse_basics(self):
        result = self._parse(service_uuids=[OURA_DATA_SERVICE_UUID])
        assert result.parser_name == "oura"
        assert result.device_class == "wearable"
