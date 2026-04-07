"""Tests for Samsung Galaxy Watch BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.galaxy_watch import GalaxyWatchParser


@pytest.fixture
def parser():
    return GalaxyWatchParser()


def make_raw(service_uuids=None, service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_uuids=service_uuids or [],
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


WATCH_SVC_DATA = bytes.fromhex("0358e427eedb3e59ae89b632ec01")
WATCH_SVC_DATA_LONG = bytes.fromhex("1058e427eedb3e59ae89b632ec52001e1a20ec8b")
WATCH_NAMED_DATA = bytes.fromhex("009af2445b834b4c9ac7207c824000")


class TestGalaxyWatchParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "galaxy_watch"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "galaxy_watch"

    def test_device_class(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA})
        result = parser.parse(raw)
        assert result.device_class == "wearable"

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_with_local_name(self, parser):
        raw = make_raw(
            service_uuids=["fd69"],
            service_data={"fd69": WATCH_NAMED_DATA},
            local_name="Galaxy Watch Active2(6105) LE",
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_name"] == "Galaxy Watch Active2(6105) LE"

    def test_long_service_data(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA_LONG})
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(service_uuids=["fd69"])
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_name_pattern(self, parser):
        raw = make_raw(local_name="Galaxy Watch Active2(6105) LE")
        result = parser.parse(raw)
        assert result is not None

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_uuids=["fd69"], service_data={"fd69": WATCH_SVC_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == WATCH_SVC_DATA.hex()


class TestGalaxyWatchMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
