"""Tests for Phonak / Sonova hearing-aid plugin."""

import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.phonak import PhonakParser, SONOVA_COMPANY_ID


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
        name="phonak",
        company_id=SONOVA_COMPANY_ID,
        local_name_pattern=r"(?i)^(Audeo|Aud[eé]o|Na[ií]da|Virto|Sky|Phonak)",
        description="Phonak",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PhonakParser):
        pass
    return _P


class TestPhonakMatching:
    def test_match_sonova_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=struct.pack("<H", SONOVA_COMPANY_ID) + b"\x01\x02")
        assert len(registry.match(ad)) == 1

    def test_match_audeo_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Audeo Lumity R")
        assert len(registry.match(ad)) == 1

    def test_match_phonak_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Phonak Naida")
        assert len(registry.match(ad)) == 1


class TestPhonakParsing:
    def test_cid_payload_captured(self):
        cid = struct.pack("<H", SONOVA_COMPANY_ID)
        ad = _make_ad(manufacturer_data=cid + b"\x10\x20\x30")
        result = PhonakParser().parse(ad)
        assert result.metadata["cid_match"] is True
        assert result.metadata["payload_hex"] == "102030"

    def test_product_line_from_name(self):
        result = PhonakParser().parse(_make_ad(local_name="Audeo Lumity"))
        assert result.metadata["product_line"] == "audeo"

    def test_returns_none_unrelated(self):
        assert PhonakParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = PhonakParser().parse(_make_ad(local_name="Phonak"))
        assert result.parser_name == "phonak"
        assert result.device_class == "hearing_aid"
