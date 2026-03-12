"""Tests for Tile tracker plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.tile import TileParser


@pytest.fixture
def parser():
    return TileParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


TILE_DATA = bytes([0x01, 0x02, 0x03, 0x04, 0x05])


class TestTileParsing:
    def test_parse_valid_tile(self, parser):
        raw = make_raw(service_data={"feed": TILE_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"feed": TILE_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "tile"

    def test_device_class_tracker(self, parser):
        raw = make_raw(service_data={"feed": TILE_DATA})
        result = parser.parse(raw)
        assert result.device_class == "tracker"

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac:service_data_hex)[:16]."""
        raw = make_raw(
            service_data={"feed": TILE_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{TILE_DATA.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"feed": TILE_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"feed": TILE_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == TILE_DATA.hex()

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Tile"


class TestTileMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": TILE_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(service_data={"feed": b""})
        assert parser.parse(raw) is None
