"""Tests for InteraXon Muse EEG headband plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.muse import (
    MuseParser, INTERAXON_COMPANY_ID, MUSE_SERVICE_UUID, MUSES_DEVICE_TYPE_CODES,
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
        name="muse",
        company_id=INTERAXON_COMPANY_ID,
        service_uuid=MUSE_SERVICE_UUID,
        local_name_pattern=r"^MuseS?-",
        description="Muse",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(MuseParser):
        pass
    return _P


def _mfr(byte0: int, byte1: int) -> bytes:
    return struct.pack("<H", INTERAXON_COMPANY_ID) + bytes([byte0, byte1])


class TestMuseMatching:
    def test_match_fe8d_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MUSE_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(0, 0))
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Muse-AABB")
        assert len(registry.match(ad)) == 1


class TestMuseGeneration:
    def test_muses_from_mfr_byte_5(self):
        result = MuseParser().parse(_make_ad(manufacturer_data=_mfr(0, 0x05)))
        assert result.metadata["generation"] == "MuseS"
        assert result.metadata["device_type_code"] == 0x05

    def test_muses_from_mfr_byte_6(self):
        result = MuseParser().parse(_make_ad(manufacturer_data=_mfr(0, 0x06)))
        assert result.metadata["generation"] == "MuseS"

    def test_muses_from_mfr_byte_7(self):
        result = MuseParser().parse(_make_ad(manufacturer_data=_mfr(0, 0x07)))
        assert result.metadata["generation"] == "MuseS"

    def test_muse2_from_mfr_other(self):
        result = MuseParser().parse(_make_ad(manufacturer_data=_mfr(0, 0x02)))
        assert result.metadata["generation"] == "Muse_or_Muse2"

    def test_muses_from_name_prefix(self):
        result = MuseParser().parse(_make_ad(local_name="MuseS-AABB"))
        assert result.metadata["generation"] == "MuseS"

    def test_muse_from_name_prefix(self):
        result = MuseParser().parse(_make_ad(local_name="Muse-AABB"))
        assert result.metadata["generation"] == "Muse_or_Muse2"


class TestMuseIdentity:
    def test_mac_suffix_extracted(self):
        result = MuseParser().parse(_make_ad(local_name="Muse-aabb"))
        assert result.metadata["mac_suffix"] == "AABB"

    def test_identity_uses_mac_suffix(self):
        ad = _make_ad(local_name="Muse-DEAD", mac_address="11:22:33:44:55:66")
        result = MuseParser().parse(ad)
        expected = hashlib.sha256(b"muse:DEAD").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert MuseParser().parse(_make_ad(local_name="EEG")) is None

    def test_parse_basics(self):
        result = MuseParser().parse(_make_ad(service_uuids=[MUSE_SERVICE_UUID]))
        assert result.parser_name == "muse"
        assert result.device_class == "wearable"
