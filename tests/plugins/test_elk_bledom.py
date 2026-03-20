"""Tests for ELK-BLEDOM LED light plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.elk_bledom import ElkBledomParser


@pytest.fixture
def parser():
    return ElkBledomParser()


def make_raw(local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(local_name=local_name, **defaults)


class TestElkBledomParsing:
    def test_parse_valid_returns_result(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_with_suffix(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM  ")
        result = parser.parse(raw)
        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM")
        result = parser.parse(raw)
        assert result.parser_name == "elk_bledom"

    def test_beacon_type(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM")
        result = parser.parse(raw)
        assert result.beacon_type == "elk_bledom"

    def test_device_class_light(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM")
        result = parser.parse(raw)
        assert result.device_class == "light"

    def test_identity_hash_format(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(local_name="ELK-BLEDOM")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "ELK-BLEDOM"


class TestElkBledomRejection:
    def test_returns_none_no_name(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_name(self, parser):
        raw = make_raw(local_name="SomeOtherLight")
        assert parser.parse(raw) is None

    def test_returns_none_partial_name(self, parser):
        raw = make_raw(local_name="ELK")
        assert parser.parse(raw) is None
