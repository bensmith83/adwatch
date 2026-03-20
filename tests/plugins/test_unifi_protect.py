"""Tests for UniFi Protect camera plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.unifi_protect import UniFiProtectParser


UNIFI_UUID = "054e1ac8-1ad8-4c10-a0de-e55fc4f268e5"

MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def parser():
    return UniFiProtectParser()


def make_raw(local_name=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=MAC,
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        local_name=local_name,
        service_uuids=service_uuids or [],
        **defaults,
    )


class TestUniFiProtectParsing:
    def test_parse_with_name_returns_result(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_with_uuid_returns_result(self, parser):
        raw = make_raw(service_uuids=[UNIFI_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parse_with_both(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus", service_uuids=[UNIFI_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus")
        result = parser.parse(raw)
        assert result.parser_name == "unifi_protect"

    def test_beacon_type(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus")
        result = parser.parse(raw)
        assert result.beacon_type == "unifi_protect"

    def test_device_class_camera(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus")
        result = parser.parse(raw)
        assert result.device_class == "camera"

    def test_identity_hash_format(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(local_name="UCK-G2-Plus")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "UCK-G2-Plus"


class TestUniFiProtectRejection:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(local_name="SomeCamera")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_partial_name(self, parser):
        """Name must start with UCK."""
        raw = make_raw(local_name="MyUCK")
        assert parser.parse(raw) is None
