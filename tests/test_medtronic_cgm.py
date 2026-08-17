"""Tests for the Medtronic Guardian CGM transmitter plugin.

Sources:
  - apk-ble-hunting/reports/medtronic-diabetes-guardianconnect_passive.md:
    discovery is *exactly* "does the AD service-UUID list contain
    b0202e40-008b-11e3-a5f3-0002a5d5c51b" (the GST service).
  - apk-ble-hunting/reports/medtronic-diabetes-guardian_passive.md:
    Guardian 4 scans unfiltered and matches in Dart; the services it builds are
    0xFE82 (Medtronic SIG member UUID / SAKE secure channel) and 0x181F
    (SIG CGM Service). 0x181F is vendor-agnostic so it is never a match
    criterion on its own — only reported as metadata.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.medtronic_cgm import (
    CGM_SERVICE_UUID,
    GST_SERVICE_UUID,
    MEDTRONIC_SAKE_UUID,
    MedtronicCgmParser,
)


@pytest.fixture
def parser():
    return MedtronicCgmParser()


def make_raw(**kwargs):
    defaults = dict(
        timestamp="2026-08-16T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="medtronic_cgm",
        service_uuid=(GST_SERVICE_UUID, MEDTRONIC_SAKE_UUID),
        description="Medtronic Guardian CGM",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(MedtronicCgmParser):
        pass

    return _P


class TestConstants:
    def test_gst_uuid(self):
        assert GST_SERVICE_UUID == "b0202e40-008b-11e3-a5f3-0002a5d5c51b"

    def test_sake_uuid(self):
        assert MEDTRONIC_SAKE_UUID == "fe82"

    def test_cgm_uuid(self):
        assert CGM_SERVICE_UUID == "181f"


class TestMatching:
    def test_matches_gst_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(make_raw(service_uuids=[GST_SERVICE_UUID]))) == 1

    def test_matches_sake_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(make_raw(service_uuids=["FE82"]))) == 1

    def test_does_not_register_on_generic_cgm_service(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(make_raw(service_uuids=[CGM_SERVICE_UUID])) == []


class TestParsing:
    def test_guardian_connect_by_gst_uuid(self, parser):
        result = parser.parse(make_raw(service_uuids=[GST_SERVICE_UUID]))
        assert result is not None
        assert result.metadata["model"] == "Guardian Connect / Guardian Sensor transmitter"
        assert result.metadata["matched_service"] == GST_SERVICE_UUID
        assert result.parser_name == "medtronic_cgm"
        assert result.beacon_type == "medtronic_cgm"
        assert result.device_class == "medical"

    def test_guardian_4_by_sake_uuid(self, parser):
        result = parser.parse(make_raw(service_uuids=["fe82"]))
        assert result is not None
        assert result.metadata["model"] == "Guardian 4 transmitter"
        assert result.metadata["matched_service"] == MEDTRONIC_SAKE_UUID

    def test_gst_wins_over_sake_when_both_present(self, parser):
        result = parser.parse(make_raw(service_uuids=[GST_SERVICE_UUID, "fe82"]))
        assert result.metadata["matched_service"] == GST_SERVICE_UUID

    def test_cgm_service_reported_as_metadata_only(self, parser):
        result = parser.parse(make_raw(service_uuids=["fe82", "181f"]))
        assert result.metadata["has_sig_cgm_service"] is True

    def test_cgm_service_absent_is_not_flagged(self, parser):
        result = parser.parse(make_raw(service_uuids=["fe82"]))
        assert "has_sig_cgm_service" not in result.metadata

    def test_device_name_recorded(self, parser):
        result = parser.parse(make_raw(service_uuids=[GST_SERVICE_UUID], local_name="GS123456H"))
        assert result.metadata["device_name"] == "GS123456H"

    def test_full_128bit_form_of_sake_uuid(self, parser):
        raw = make_raw(service_uuids=["0000fe82-0000-1000-8000-00805f9b34fb"])
        assert parser.parse(raw) is not None


class TestIdentity:
    def test_identity_hash_is_mac_based(self, parser):
        result = parser.parse(make_raw(service_uuids=[GST_SERVICE_UUID]))
        assert result.identifier_hash == hashlib.sha256(
            b"medtronic_cgm:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]

    def test_different_mac_different_hash(self, parser):
        a = parser.parse(make_raw(service_uuids=[GST_SERVICE_UUID]))
        b = parser.parse(make_raw(service_uuids=[GST_SERVICE_UUID], mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash != b.identifier_hash


class TestNegatives:
    def test_generic_cgm_service_alone_returns_none(self, parser):
        assert parser.parse(make_raw(service_uuids=["181f"])) is None

    def test_unrelated_ad_returns_none(self, parser):
        assert parser.parse(make_raw(service_uuids=["febc"], local_name="Dexcom99")) is None

    def test_no_service_uuids_returns_none(self, parser):
        assert parser.parse(make_raw()) is None

    def test_storage_schema_is_none(self, parser):
        assert parser.storage_schema() is None
