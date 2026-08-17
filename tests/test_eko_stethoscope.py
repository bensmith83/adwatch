"""Tests for Eko digital stethoscope plugin.

Per apk-ble-hunting/reports/ekodevices-android_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.eko_stethoscope import (
    EkoStethoscopeParser,
    EKO_SERVICE_UUIDS,
    EKO_GENERATIONS,
    EKO_DFU_UUIDS,
    EKO_NAME_PATTERN,
    LEGACY_SHARED_UUID,
    CORE2_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-08-16T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="eko_stethoscope",
        service_uuid=EKO_SERVICE_UUIDS,
        local_name_pattern=EKO_NAME_PATTERN,
        description="Eko",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(EkoStethoscopeParser):
        pass

    return registry


class TestMatching:
    def test_all_service_uuids_match(self):
        reg = _register(ParserRegistry())
        for uuid in EKO_SERVICE_UUIDS:
            assert len(reg.match(_make_ad(service_uuids=[uuid]))) == 1, uuid

    def test_uppercase_uuid_matches(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(service_uuids=[CORE2_UUID.upper()]))) == 1

    def test_name_matches(self):
        reg = _register(ParserRegistry())
        for name in ("Eko CORE 1234", "eko duo", "EKO CORE2 DFU"):
            assert len(reg.match(_make_ad(local_name=name))) == 1, name

    def test_unrelated_does_not_match(self):
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(service_uuids=["fd6f"], local_name="Echo Dot")) == []


class TestGenerationMapping:
    def test_each_uuid_maps_to_a_generation(self):
        p = EkoStethoscopeParser()
        for uuid, generation in EKO_GENERATIONS.items():
            r = p.parse(_make_ad(service_uuids=[uuid]))
            assert r is not None, uuid
            assert r.metadata["generation"] == generation

    def test_core2_uuid(self):
        r = EkoStethoscopeParser().parse(_make_ad(service_uuids=[CORE2_UUID]))
        assert r.metadata["generation"] == "CORE2 (E6)"
        assert r.device_class == "medical"

    def test_legacy_shared_uuid_without_name_is_ambiguous(self):
        r = EkoStethoscopeParser().parse(_make_ad(service_uuids=[LEGACY_SHARED_UUID]))
        assert r.metadata["generation"] == "CORE (E4) / DUO (E5) / DUO 1.5"
        assert r.metadata["generation_ambiguous"] is True

    def test_legacy_shared_uuid_tiebreaks_on_name(self):
        p = EkoStethoscopeParser()
        core = p.parse(_make_ad(service_uuids=[LEGACY_SHARED_UUID], local_name="Eko CORE 88"))
        assert core.metadata["generation"] == "CORE (E4)"
        assert core.metadata["generation_ambiguous"] is False
        duo = p.parse(_make_ad(service_uuids=[LEGACY_SHARED_UUID], local_name="Eko DUO 88"))
        assert duo.metadata["generation"] == "DUO (E5)"

    def test_core2_name_beats_core_substring(self):
        r = EkoStethoscopeParser().parse(_make_ad(local_name="Eko CORE2 77"))
        assert r.metadata["generation"] == "CORE2 (E6)"


class TestDfuDetection:
    def test_dfu_service_uuid_flags_update_mode(self):
        p = EkoStethoscopeParser()
        for uuid in EKO_DFU_UUIDS:
            r = p.parse(_make_ad(service_uuids=[uuid]))
            assert r.metadata["dfu_mode"] is True, uuid

    def test_dfu_name_marker(self):
        r = EkoStethoscopeParser().parse(_make_ad(local_name="Eko CORE2 DFU"))
        assert r.metadata["dfu_mode"] is True

    def test_update_required_name_marker(self):
        r = EkoStethoscopeParser().parse(
            _make_ad(service_uuids=[CORE2_UUID], local_name="Eko CORE update required"))
        assert r.metadata["dfu_mode"] is True

    def test_normal_operation_is_not_dfu(self):
        r = EkoStethoscopeParser().parse(_make_ad(service_uuids=[CORE2_UUID]))
        assert r.metadata["dfu_mode"] is False


class TestParsing:
    def test_no_telemetry_is_claimed(self):
        r = EkoStethoscopeParser().parse(_make_ad(service_uuids=[CORE2_UUID]))
        assert r.metadata["telemetry"] == "connect_required"
        assert r.metadata["vendor"] == "Eko"

    def test_identity_is_mac_based(self):
        r = EkoStethoscopeParser().parse(_make_ad(service_uuids=[CORE2_UUID]))
        assert r.identifier_hash == hashlib.sha256(
            b"eko:AA:BB:CC:DD:EE:FF").hexdigest()[:16]

    def test_device_name_surfaced(self):
        r = EkoStethoscopeParser().parse(_make_ad(local_name="Eko DUO 4412"))
        assert r.metadata["device_name"] == "Eko DUO 4412"

    def test_returns_none_for_unrelated(self):
        assert EkoStethoscopeParser().parse(
            _make_ad(service_uuids=["fd6f"], local_name="Ekobrew")) is None
