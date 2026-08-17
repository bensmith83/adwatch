"""Tests for the Therabody PowerDot / SmartMio EMS pod plugin.

Per apk-ble-hunting/reports/therabody-powerdot_passive.md — prefix-matched
device names plus two (possibly advertised) vendor service UUIDs.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.powerdot import (
    PowerDotParser,
    POWERDOT_SERVICE_UUIDS,
    POWERDOT_NAME_PATTERN,
    POWERDOT_STIM_SERVICE_UUID,
    POWERDOT_LEGACY_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "C8:FD:19:11:22:33",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="powerdot",
        service_uuid=POWERDOT_SERVICE_UUIDS,
        local_name_pattern=POWERDOT_NAME_PATTERN,
        description="PowerDot",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PowerDotParser):
        pass

    return _P


class TestPowerDotMatching:
    def test_matches_powerdot2_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="PowerDot2-4F21"))) == 1

    def test_matches_stim_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[POWERDOT_STIM_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_legacy_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[POWERDOT_LEGACY_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_does_not_match_unrelated_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="PowerBank 2")) == []


class TestPowerDotNameVariants:
    def test_powerdot2_is_protocol_v2(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        assert result.metadata["model"] == "PowerDot 2.0"
        assert result.metadata["protocol_generation"] == "v2"

    def test_powerdot_mt_is_medical_firmware(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDotMT7"))
        assert result.metadata["model"] == "PowerDot MT"
        assert result.metadata["protocol_generation"] == "v2mt"

    def test_smartmio_is_protocol_v1(self):
        result = PowerDotParser().parse(_make_ad(local_name="SmartMio12"))
        assert result.metadata["model"] == "SmartMio (GEN-1)"
        assert result.metadata["protocol_generation"] == "v1"

    def test_a_prefixed_smartmio(self):
        result = PowerDotParser().parse(_make_ad(local_name="aSmartMio12"))
        assert result.metadata["protocol_generation"] == "v1"

    def test_a_prefixed_powerdot_is_gen1(self):
        result = PowerDotParser().parse(_make_ad(local_name="aPowerDot99"))
        assert result.metadata["model"] == "PowerDot (GEN-1)"
        assert result.metadata["protocol_generation"] == "v1"

    def test_gen_1_prefix(self):
        result = PowerDotParser().parse(_make_ad(local_name="GEN_1_0007"))
        assert result.metadata["protocol_generation"] == "v1"
        assert result.metadata["confidence"] == "medium"

    def test_brand_prefix_is_high_confidence(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        assert result.metadata["confidence"] == "high"


class TestPowerDotParsing:
    def test_parses_presence(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        assert result is not None
        assert result.parser_name == "powerdot"
        assert result.beacon_type == "powerdot"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Therabody"

    def test_records_name_suffix(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        assert result.metadata["name_suffix"] == "-4F21"

    def test_uuid_only_match_has_unknown_model(self):
        ad = _make_ad(service_uuids=[POWERDOT_STIM_SERVICE_UUID])
        result = PowerDotParser().parse(ad)
        assert result is not None
        assert result.metadata["match_basis"] == "service_uuid"
        assert "model" not in result.metadata

    def test_flags_sensitive_category(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "muscle_stimulation"

    def test_no_telemetry_claimed(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_identity_prefers_name_suffix(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2-4F21"))
        expected = hashlib.sha256(b"powerdot:PowerDot2-4F21").hexdigest()[:16]
        assert result.identifier_hash == expected
        assert result.metadata["identity_basis"] == "local_name"

    def test_identity_survives_mac_rotation(self):
        a = PowerDotParser().parse(
            _make_ad(local_name="PowerDot2-4F21", mac_address="C8:FD:19:11:22:33"))
        b = PowerDotParser().parse(
            _make_ad(local_name="PowerDot2-4F21", mac_address="DE:AD:BE:EF:00:01"))
        assert a.identifier_hash == b.identifier_hash

    def test_identity_falls_back_to_mac_without_suffix(self):
        result = PowerDotParser().parse(_make_ad(local_name="PowerDot2"))
        expected = hashlib.sha256(b"powerdot:C8:FD:19:11:22:33").hexdigest()[:16]
        assert result.identifier_hash == expected
        assert result.metadata["identity_basis"] == "mac"

    def test_rejects_unrelated_name(self):
        assert PowerDotParser().parse(_make_ad(local_name="Compex Mini")) is None

    def test_rejects_empty_ad(self):
        assert PowerDotParser().parse(_make_ad()) is None

    def test_storage_schema_is_none(self):
        assert PowerDotParser().storage_schema() is None
