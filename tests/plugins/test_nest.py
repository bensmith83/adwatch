"""Tests for Nest / Google Home plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.nest import NestParser


@pytest.fixture
def parser():
    return NestParser()


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


NEST_DATA = bytes.fromhex("1001000200e11900546313520066166401")


class TestNestParsing:
    def test_parse_valid_nest(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "nest"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "nest"

    def test_device_class_smart_home(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.device_class == "smart_home"

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac:service_data_hex)[:16]."""
        raw = make_raw(
            service_data={"feaf": NEST_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{NEST_DATA.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == NEST_DATA.hex()

    def test_metadata_payload_hex(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == NEST_DATA.hex()

    def test_metadata_payload_length(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == len(NEST_DATA)

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Nest"

    def test_metadata_includes_local_name_hint(self, parser):
        """Metadata should include local_name if available."""
        raw = make_raw(service_data={"feaf": NEST_DATA}, local_name="NW3J0")
        result = parser.parse(raw)
        assert result.metadata["device_code"] == "NW3J0"

    def test_metadata_device_code_none(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.metadata["device_code"] is None

    def test_api_router_without_db(self, parser):
        assert parser.api_router() is None

    def test_api_router_with_db(self, parser):
        router = parser.api_router(db=object())
        assert router is not None


class TestNestMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": NEST_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(service_data={"feaf": b""})
        assert parser.parse(raw) is None
