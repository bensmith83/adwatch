"""Tests for Pokemon GO Plus + BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.pokemon_go_plus import PokemonGoPlusParser


@pytest.fixture
def parser():
    return PokemonGoPlusParser()


def make_raw(manufacturer_data=None, service_uuids=None, service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_uuids=service_uuids or [],
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


POKEMON_MFR = bytes.fromhex("530501aede00f0be000000000000000002")


class TestPokemonGoPlusParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR, local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR, local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert result.parser_name == "pokemon_go_plus"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR, local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert result.beacon_type == "pokemon_go_plus"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR, local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert result.device_class == "gaming_accessory"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR, local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_match_by_name(self, parser):
        raw = make_raw(local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_company_id(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR)
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=POKEMON_MFR, local_name="Pokemon GO Plus +")
        result = parser.parse(raw)
        assert result.raw_payload_hex == POKEMON_MFR.hex()


class TestPokemonGoPlusMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(manufacturer_data=b"\x01\x02\x03\x04")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None
