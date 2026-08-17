"""Tests for the Biobeat BB-613WP BP/SpO2 monitor plugin.

Per apk-ble-hunting/reports/biobeat-abpm_passive.md:
  - Scan filter = advertised 128-bit service UUID
    3FD4750B-CFF6-405C-AF2C-BC0E76193183 (note: NOT the GATT service
    2905B9AA-6B1F-4C49-9C26-9BFC88350290 the characteristics live under).
  - Devices are accepted only when the advertised local name is non-empty;
    there is no prefix to match.
  - No manufacturer-data / service-data parsing exists in the app.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.biobeat import (
    BIOBEAT_ADVERTISED_SERVICE_UUID,
    BIOBEAT_GATT_SERVICE_UUID,
    BiobeatParser,
)


@pytest.fixture
def parser():
    return BiobeatParser()


def make_raw(**kwargs):
    defaults = dict(
        timestamp="2026-08-16T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="biobeat",
        service_uuid=(BIOBEAT_ADVERTISED_SERVICE_UUID, BIOBEAT_GATT_SERVICE_UUID),
        description="Biobeat",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(BiobeatParser):
        pass

    return _P


class TestConstants:
    def test_advertised_uuid(self):
        assert BIOBEAT_ADVERTISED_SERVICE_UUID == "3fd4750b-cff6-405c-af2c-bc0e76193183"

    def test_gatt_uuid_is_distinct(self):
        assert BIOBEAT_GATT_SERVICE_UUID == "2905b9aa-6b1f-4c49-9c26-9bfc88350290"
        assert BIOBEAT_GATT_SERVICE_UUID != BIOBEAT_ADVERTISED_SERVICE_UUID


class TestMatching:
    def test_matches_advertised_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        raw = make_raw(service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID])
        assert len(registry.match(raw)) == 1

    def test_matches_uppercase_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        raw = make_raw(service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID.upper()])
        assert len(registry.match(raw)) == 1

    def test_does_not_match_other_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(make_raw(service_uuids=["180a"])) == []


class TestParsing:
    def test_advertised_uuid_parses(self, parser):
        result = parser.parse(make_raw(
            service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID],
            local_name="BB6130001",
        ))
        assert result is not None
        assert result.parser_name == "biobeat"
        assert result.beacon_type == "biobeat"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Biobeat"
        assert result.metadata["model"] == "BB-613WP cuffless BP/SpO2 monitor"
        assert result.metadata["matched_service"] == "advertised"
        assert result.metadata["device_name"] == "BB6130001"

    def test_gatt_uuid_parses_as_secondary(self, parser):
        result = parser.parse(make_raw(service_uuids=[BIOBEAT_GATT_SERVICE_UUID]))
        assert result is not None
        assert result.metadata["matched_service"] == "gatt"

    def test_named_flag_mirrors_app_gate(self, parser):
        with_name = parser.parse(make_raw(
            service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID], local_name="BB6130001"
        ))
        without_name = parser.parse(make_raw(service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID]))
        assert with_name.metadata["app_discoverable"] is True
        assert without_name.metadata["app_discoverable"] is False
        assert "device_name" not in without_name.metadata

    def test_empty_name_is_not_discoverable(self, parser):
        result = parser.parse(make_raw(
            service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID], local_name=""
        ))
        assert result.metadata["app_discoverable"] is False


class TestIdentity:
    def test_identity_hash_is_mac_based(self, parser):
        result = parser.parse(make_raw(service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID]))
        assert result.identifier_hash == hashlib.sha256(
            b"biobeat:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]

    def test_different_mac_different_hash(self, parser):
        a = parser.parse(make_raw(service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID]))
        b = parser.parse(make_raw(
            service_uuids=[BIOBEAT_ADVERTISED_SERVICE_UUID], mac_address="11:22:33:44:55:66"
        ))
        assert a.identifier_hash != b.identifier_hash


class TestNegatives:
    def test_unrelated_returns_none(self, parser):
        assert parser.parse(make_raw(service_uuids=["fd6f"], local_name="BB6130001")) is None

    def test_name_alone_returns_none(self, parser):
        assert parser.parse(make_raw(local_name="BioBeat")) is None

    def test_storage_schema_is_none(self, parser):
        assert parser.storage_schema() is None
