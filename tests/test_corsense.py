"""Tests for the Elite HRV CorSense finger HRV sensor plugin.

Per apk-ble-hunting/reports/elite-hrv_passive.md: the Elite HRV app scans on the
SIG Heart Rate Service `0x180D` only (vendor-agnostic — deliberately NOT a match
criterion here) and classifies the strap brand from the advertised name, with
`isCorSense(name)` gating the CorSense-specific GATT reads. The only reusable
passive discriminator for Elite HRV's own hardware is that name.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.corsense import (
    CorSenseParser,
    CORSENSE_NAME_TOKEN,
    SIG_HEART_RATE_SERVICE_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "CorSense 1234",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="corsense",
        local_name_pattern=r"(?i)corsense",
        description="CorSense",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(CorSenseParser):
        pass

    return _P


class TestCorSenseConstants:
    def test_name_token(self):
        assert CORSENSE_NAME_TOKEN == "corsense"

    def test_sig_hr_uuid_constant(self):
        assert SIG_HEART_RATE_SERVICE_UUID == "180d"


class TestCorSenseMatching:
    def test_match_name_case_insensitive(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="corsense"))) == 1
        assert len(registry.match(_make_ad(local_name="CorSense 42"))) == 1

    def test_sig_hr_service_alone_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Polar H10 A1B2C3D4", service_uuids=["180d"])
        assert registry.match(ad) == []


class TestCorSenseParse:
    def test_name_match_parses(self):
        result = CorSenseParser().parse(_make_ad(local_name="CorSense 1234"))
        assert result is not None
        assert result.parser_name == "corsense"
        assert result.device_class == "wearable"
        assert result.metadata["vendor"] == "Elite HRV"
        assert result.metadata["device_name"] == "CorSense 1234"
        assert result.metadata["name_suffix"] == "1234"

    def test_bare_name_has_no_suffix(self):
        result = CorSenseParser().parse(_make_ad(local_name="CorSense"))
        assert result is not None
        assert "name_suffix" not in result.metadata

    def test_hr_service_recorded_as_enrichment(self):
        result = CorSenseParser().parse(
            _make_ad(local_name="CorSense", service_uuids=["180d"])
        )
        assert result.metadata["heart_rate_service_advertised"] is True

    def test_hr_service_absent_not_claimed(self):
        result = CorSenseParser().parse(_make_ad(local_name="CorSense"))
        assert "heart_rate_service_advertised" not in result.metadata

    def test_hr_service_alone_returns_none(self):
        assert CorSenseParser().parse(
            _make_ad(local_name="Some Strap", service_uuids=["180d"])
        ) is None

    def test_identity_hash_uses_name(self):
        result = CorSenseParser().parse(_make_ad(local_name="CorSense 1234"))
        expected = hashlib.sha256(b"corsense:CorSense 1234").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_telemetry_claimed(self):
        result = CorSenseParser().parse(_make_ad(local_name="CorSense"))
        assert result.raw_payload_hex == ""
        assert "heart_rate_bpm" not in result.metadata

    def test_unrelated_returns_none(self):
        assert CorSenseParser().parse(_make_ad(local_name="HRM-Dual:012345")) is None

    def test_no_name_returns_none(self):
        assert CorSenseParser().parse(_make_ad(local_name=None)) is None
