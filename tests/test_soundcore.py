"""Tests for Anker Soundcore best-effort plugin."""

import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.soundcore import SoundcoreParser, ANKER_COMPANY_ID


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="soundcore", company_id=ANKER_COMPANY_ID,
                     local_name_pattern=r"^[Ss]oundcore ", description="Soundcore",
                     version="1.0.0", core=False, registry=registry)
    class _P(SoundcoreParser):
        pass
    return _P


def _mfr(payload: bytes = b"\x42\x00\x00") -> bytes:
    return struct.pack("<H", ANKER_COMPANY_ID) + payload


class TestSoundcore:
    def test_match_anker_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_soundcore_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Soundcore Liberty Air 2")
        assert len(registry.match(ad)) == 1

    def test_product_code_byte(self):
        result = SoundcoreParser().parse(_make_ad(manufacturer_data=_mfr(b"\x42\xff")))
        assert result.metadata["product_code_byte"] == 0x42

    def test_model_hint_from_name(self):
        result = SoundcoreParser().parse(_make_ad(local_name="Soundcore Motion+"))
        assert result.metadata["model_hint"] == "Motion+"

    def test_returns_none_unrelated(self):
        assert SoundcoreParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = SoundcoreParser().parse(_make_ad(local_name="Soundcore X"))
        assert result.parser_name == "soundcore"
        assert result.device_class == "audio"
