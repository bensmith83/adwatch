"""Tests for Polestar Digital Key plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.polestar_key import PolestarKeyParser


@pytest.fixture
def parser():
    return PolestarKeyParser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-09T00:00:00+00:00",
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


POLESTAR_UUID = "bf327664-cc10-9e54-5dd4-41c88fb4f257"


class TestPolestarKeyParsing:
    def test_parse_by_name_and_uuid(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_by_uuid_only(self, parser):
        raw = make_raw(service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parse_by_name_polestar3(self, parser):
        raw = make_raw(local_name="Polestar3", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "Polestar 3"

    def test_parser_name(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result.parser_name == "polestar_key"

    def test_beacon_type(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result.beacon_type == "polestar_digital_key"

    def test_device_class_vehicle(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result.device_class == "vehicle"

    def test_identity_hash_format(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            local_name="Polestar2",
            service_uuids=[POLESTAR_UUID],
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_metadata_model(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result.metadata["model"] == "Polestar 2"

    def test_metadata_device_name(self, parser):
        raw = make_raw(local_name="Polestar2", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Polestar2"

    def test_no_match_unrelated(self, parser):
        raw = make_raw(service_uuids=["1234"], local_name="Tesla")
        result = parser.parse(raw)
        assert result is None

    def test_parse_by_name_only(self, parser):
        """Name-only match — no Polestar service UUID present."""
        raw = make_raw(local_name="Polestar2")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "Polestar 2"

    def test_no_match_empty(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result is None

    def test_volvo_name_match(self, parser):
        """Volvo uses the same Polestar/Volvo digital key platform."""
        raw = make_raw(local_name="Volvo XC40", service_uuids=[POLESTAR_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_name"] == "Volvo XC40"
