"""Tests for Oura Ring plugin."""

import struct
import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.oura import (
    OuraParser, OURA_COMPANY_ID,
    OURA_DATA_SERVICE_UUID, OURA_CHARGER_SERVICE_UUID, OURA_DFU_SERVICE_UUID,
    HARDWARE_TYPES, RING_MODES,
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
        service_uuid=(OURA_DATA_SERVICE_UUID, OURA_CHARGER_SERVICE_UUID, OURA_DFU_SERVICE_UUID),
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

    def test_dfu_mode(self):
        result = self._parse(service_uuids=[OURA_DFU_SERVICE_UUID])
        assert result.metadata["device_kind"] == "ring"
        assert result.metadata["mode"] == "BOOTLOADER"

    def test_mode_and_hwtype_nibbles(self):
        # payload[1] = (hwtype << 4) | mode = (0x02 << 4) | 0x01 = 0x21
        result = self._parse(manufacturer_data=_mfr(bytes([0x00, 0x21])))
        assert result.metadata["mode_code"] == 1
        assert result.metadata["mode"] == "OPERATING"
        assert result.metadata["hardware_type_code"] == 2
        assert result.metadata["hardware_type"] == "GEN4"

    def test_color_and_i_nibbles(self):
        # payload[2] = (color << 4) | i = (5 << 4) | 3 = 0x53
        result = self._parse(manufacturer_data=_mfr(bytes([0x00, 0x00, 0x53])))
        assert result.metadata["i_nibble"] == 3
        assert result.metadata["color_code"] == 5

    def test_design_code(self):
        result = self._parse(manufacturer_data=_mfr(bytes([0x00, 0x00, 0x00, 0x07])))
        assert result.metadata["design_code"] == 7

    def test_returns_none_unrelated(self):
        assert self._parse(local_name="Other") is None

    def test_parse_basics(self):
        result = self._parse(service_uuids=[OURA_DATA_SERVICE_UUID])
        assert result.parser_name == "oura"
        assert result.device_class == "wearable"
