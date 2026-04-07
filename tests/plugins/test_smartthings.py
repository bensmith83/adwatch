"""Tests for Samsung SmartThings BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.smartthings import SmartThingsParser


@pytest.fixture
def parser():
    return SmartThingsParser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


class TestSmartThingsParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_uuids=["1122"], local_name="S98039bf21cd187e2C")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=["1122"], local_name="S98039bf21cd187e2C")
        result = parser.parse(raw)
        assert result.parser_name == "smartthings"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=["1122"], local_name="S98039bf21cd187e2C")
        result = parser.parse(raw)
        assert result.beacon_type == "smartthings"

    def test_device_class(self, parser):
        raw = make_raw(service_uuids=["1122"], local_name="S98039bf21cd187e2C")
        result = parser.parse(raw)
        assert result.device_class == "smart_home"

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=["1122"], local_name="S98039bf21cd187e2C")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_id(self, parser):
        raw = make_raw(service_uuids=["1122"], local_name="S98039bf21cd187e2C")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "98039bf21cd187e2"

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(service_uuids=["1122"])
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_name_only(self, parser):
        raw = make_raw(local_name="S201b91dbacb104cdC")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_id"] == "201b91dbacb104cd"

    def test_different_device_ids(self, parser):
        raw1 = make_raw(service_uuids=["1122"], local_name="S283da1b32aee14ddC")
        raw2 = make_raw(service_uuids=["1122"], local_name="Sed9ccb98a762300eC")
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.metadata["device_id"] == "283da1b32aee14dd"
        assert r2.metadata["device_id"] == "ed9ccb98a762300e"


class TestSmartThingsMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
