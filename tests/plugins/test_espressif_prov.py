"""Tests for Espressif BLE provisioning plugin."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.espressif_prov import EspressifProvParser


PROV_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"


@pytest.fixture
def parser():
    return EspressifProvParser()


def make_raw(service_uuids=None, local_name=None, manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-15T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


class TestEspressifProvParsing:
    def test_parses_uuid_only(self, parser):
        raw = make_raw(service_uuids=[PROV_UUID])
        result = parser.parse(raw)
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        result = parser.parse(make_raw(service_uuids=[PROV_UUID]))
        assert result.parser_name == "espressif_prov"

    def test_beacon_type(self, parser):
        result = parser.parse(make_raw(service_uuids=[PROV_UUID]))
        assert result.beacon_type == "espressif_prov"

    def test_device_class(self, parser):
        result = parser.parse(make_raw(service_uuids=[PROV_UUID]))
        assert result.device_class == "provisioning"

    def test_uppercase_uuid_match(self, parser):
        raw = make_raw(service_uuids=[PROV_UUID.upper()])
        result = parser.parse(raw)
        assert result is not None

    def test_captures_local_name_hint(self, parser):
        raw = make_raw(service_uuids=[PROV_UUID], local_name="PROV_AB12")
        result = parser.parse(raw)
        assert result.metadata["device_hint"] == "PROV_AB12"

    def test_no_hint_when_name_empty(self, parser):
        raw = make_raw(service_uuids=[PROV_UUID])
        result = parser.parse(raw)
        assert "device_hint" not in result.metadata

    def test_vendor_confirmed_with_espressif_cid(self, parser):
        raw = make_raw(
            service_uuids=[PROV_UUID],
            manufacturer_data=bytes.fromhex("e502abcd"),
        )
        result = parser.parse(raw)
        assert result.metadata.get("vendor_confirmed") is True

    def test_vendor_not_confirmed_with_other_cid(self, parser):
        raw = make_raw(
            service_uuids=[PROV_UUID],
            manufacturer_data=bytes.fromhex("4c00abcd"),
        )
        result = parser.parse(raw)
        assert result.metadata.get("vendor_confirmed", False) is False

    def test_identifier_hash_format(self, parser):
        result = parser.parse(make_raw(service_uuids=[PROV_UUID]))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestEspressifProvNonMatching:
    def test_returns_none_for_other_uuid(self, parser):
        raw = make_raw(service_uuids=["0000feaf-0000-1000-8000-00805f9b34fb"])
        assert parser.parse(raw) is None

    def test_returns_none_for_no_uuid(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None
