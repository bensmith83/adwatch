"""Tests for the Aktiia / Hilo cuffless blood-pressure plugin.

Per apk-ble-hunting/reports/aktiia-android-production_passive.md the app does
zero advertisement parsing (unfiltered scan, name captured and sent to the
backend, then addressed by MAC), so the only fingerprint available is the
vendor-unique 128-bit UUID family the report recommends filtering on:

  3A350001-E7CC-4D7F-9683-ED4CB1001CD1  Pod token authorization
  A6B41001-003D-4E65-9208-08F4DB958863  Pod raw-data service
  A6B41010-003D-4E65-9208-08F4DB958863  Pod HBS service
  A6B40001-003D-4E65-9208-08F4DB958863  Cuff measurement (A6B400xx family)
  B1E71568-047B-47C4-88C9-0F90E397ACF7  Cuff measurement service
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.aktiia import (
    AKTIIA_SERVICE_UUIDS,
    AktiiaParser,
    CUFF_MEASUREMENT_UUID,
    POD_RAW_DATA_UUID,
    POD_TOKEN_AUTH_UUID,
)


@pytest.fixture
def parser():
    return AktiiaParser()


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
        name="aktiia",
        service_uuid=AKTIIA_SERVICE_UUIDS,
        description="Aktiia",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(AktiiaParser):
        pass

    return _P


class TestConstants:
    def test_uuids(self):
        assert POD_TOKEN_AUTH_UUID == "3a350001-e7cc-4d7f-9683-ed4cb1001cd1"
        assert POD_RAW_DATA_UUID == "a6b41001-003d-4e65-9208-08f4db958863"
        assert CUFF_MEASUREMENT_UUID == "b1e71568-047b-47c4-88c9-0f90e397acf7"

    def test_all_registered_uuids_are_known(self):
        assert POD_TOKEN_AUTH_UUID in AKTIIA_SERVICE_UUIDS
        assert CUFF_MEASUREMENT_UUID in AKTIIA_SERVICE_UUIDS


class TestMatching:
    @pytest.mark.parametrize("uuid", list(AKTIIA_SERVICE_UUIDS))
    def test_matches_each_registered_uuid(self, uuid):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(make_raw(service_uuids=[uuid]))) == 1

    def test_does_not_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(make_raw(service_uuids=["180a"], local_name="Hilo")) == []


class TestParsing:
    def test_pod_identified(self, parser):
        result = parser.parse(make_raw(service_uuids=[POD_RAW_DATA_UUID]))
        assert result is not None
        assert result.metadata["vendor"] == "Aktiia / Hilo"
        assert result.metadata["peripheral"] == "pod"
        assert result.metadata["matched_service"] == POD_RAW_DATA_UUID

    def test_token_auth_uuid_is_pod(self, parser):
        result = parser.parse(make_raw(service_uuids=[POD_TOKEN_AUTH_UUID]))
        assert result.metadata["peripheral"] == "pod"

    def test_cuff_identified(self, parser):
        result = parser.parse(make_raw(service_uuids=[CUFF_MEASUREMENT_UUID]))
        assert result.metadata["peripheral"] == "cuff"

    def test_unregistered_vendor_base_uuid_still_decodes(self, parser):
        """Registry matching is exact, but parse() accepts any A6B4xxxx member
        of the vendor base so a differently-suffixed service still resolves."""
        result = parser.parse(make_raw(service_uuids=["a6b41099-003d-4e65-9208-08f4db958863"]))
        assert result is not None
        assert result.metadata["peripheral"] == "pod"

    def test_a6b400xx_is_cuff(self, parser):
        result = parser.parse(make_raw(service_uuids=["a6b40003-003d-4e65-9208-08f4db958863"]))
        assert result.metadata["peripheral"] == "cuff"

    def test_common_fields(self, parser):
        result = parser.parse(make_raw(service_uuids=[CUFF_MEASUREMENT_UUID], local_name="Aktiia-1234"))
        assert result.parser_name == "aktiia"
        assert result.beacon_type == "aktiia"
        assert result.device_class == "medical"
        assert result.metadata["device_name"] == "Aktiia-1234"

    def test_uppercase_uuid_accepted(self, parser):
        assert parser.parse(make_raw(service_uuids=[CUFF_MEASUREMENT_UUID.upper()])) is not None


class TestIdentity:
    def test_identity_hash_is_mac_based(self, parser):
        result = parser.parse(make_raw(service_uuids=[CUFF_MEASUREMENT_UUID]))
        assert result.identifier_hash == hashlib.sha256(
            b"aktiia:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]

    def test_different_mac_different_hash(self, parser):
        a = parser.parse(make_raw(service_uuids=[CUFF_MEASUREMENT_UUID]))
        b = parser.parse(make_raw(service_uuids=[CUFF_MEASUREMENT_UUID], mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash != b.identifier_hash


class TestNegatives:
    def test_no_uuid_returns_none(self, parser):
        assert parser.parse(make_raw(local_name="Hilo")) is None

    def test_similar_but_different_base_returns_none(self, parser):
        assert parser.parse(make_raw(service_uuids=["a6b41001-003d-4e65-9208-08f4db958864"])) is None

    def test_storage_schema_is_none(self, parser):
        assert parser.storage_schema() is None
