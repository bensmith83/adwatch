"""Tests for Senseonics Eversense CGM plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.eversense_cgm import (
    EVERSENSE_SERVICE_UUID,
    EVERSENSE_SERVICE_UUIDS,
    EversenseCgmParser,
    NORDIC_DFU_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="eversense_cgm",
        service_uuid=EVERSENSE_SERVICE_UUIDS,
        description="Eversense",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(EversenseCgmParser):
        pass
    return _P


class TestEversense:
    def test_match_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[EVERSENSE_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_parse_basics(self):
        result = EversenseCgmParser().parse(_make_ad(service_uuids=[EVERSENSE_SERVICE_UUID]))
        # Renamed from "Eversense E3 CGM": the same c3230001 UUID is the
        # Eversense 365 fingerprint too (senseonics-eversense365-us_passive.md).
        assert result.metadata["product"] == "Eversense CGM smart transmitter"
        assert result.metadata["product_family"] == "Eversense E3 / 365"
        assert result.parser_name == "eversense_cgm"
        assert result.device_class == "medical"

    def test_returns_none_unrelated(self):
        assert EversenseCgmParser().parse(_make_ad(local_name="other")) is None


class TestEversense365Enrichment:
    """apk-ble-hunting/reports/senseonics-eversense365-us_passive.md.

    The 365 transmitter carries the same c3230001 service UUID as the E3; the
    report adds the c3230002/c3230003 Phx2-variant services to watch for, and
    notes the Nordic DFU base that appears during firmware update (which is
    vendor-agnostic, so it is metadata only and never a match criterion).
    """

    def test_all_variant_uuids_registered(self):
        assert EVERSENSE_SERVICE_UUID in EVERSENSE_SERVICE_UUIDS
        assert "c3230002-9308-47ae-ac12-3d030892a211" in EVERSENSE_SERVICE_UUIDS
        assert "c3230003-9308-47ae-ac12-3d030892a211" in EVERSENSE_SERVICE_UUIDS

    @pytest.mark.parametrize("uuid", [
        "c3230001-9308-47ae-ac12-3d030892a211",
        "c3230002-9308-47ae-ac12-3d030892a211",
        "c3230003-9308-47ae-ac12-3d030892a211",
    ])
    def test_each_variant_matches_and_parses(self, uuid):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[uuid])
        assert len(registry.match(ad)) == 1
        result = EversenseCgmParser().parse(ad)
        assert result is not None
        assert result.metadata["matched_service"] == uuid

    def test_uppercase_uuid_parses(self):
        ad = _make_ad(service_uuids=[EVERSENSE_SERVICE_UUID.upper()])
        assert EversenseCgmParser().parse(ad) is not None

    def test_dfu_uuid_flagged_when_co_advertised(self):
        ad = _make_ad(service_uuids=[EVERSENSE_SERVICE_UUID, NORDIC_DFU_UUID])
        result = EversenseCgmParser().parse(ad)
        assert result.metadata["firmware_update_mode"] is True

    def test_dfu_uuid_alone_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[NORDIC_DFU_UUID])
        assert registry.match(ad) == []
        assert EversenseCgmParser().parse(ad) is None

    def test_no_dfu_flag_normally(self):
        result = EversenseCgmParser().parse(_make_ad(service_uuids=[EVERSENSE_SERVICE_UUID]))
        assert "firmware_update_mode" not in result.metadata

    def test_identity_hash_unchanged(self):
        import hashlib

        result = EversenseCgmParser().parse(_make_ad(service_uuids=[EVERSENSE_SERVICE_UUID]))
        assert result.identifier_hash == hashlib.sha256(
            b"eversense:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]
