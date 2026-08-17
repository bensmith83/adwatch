"""Tests for the PetPace smart-collar plugin.

Source: apk-ble-hunting/reports/petpace_passive.md — the app filters on an
exact Complete Local Name of "Collar"; vitals are GATT-only.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.petpace import (
    PetPaceParser,
    PETPACE_NAME,
    PETPACE_NAME_PATTERN,
    PETPACE_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="petpace",
        local_name_pattern=PETPACE_NAME_PATTERN,
        description="PetPace",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PetPaceParser):
        pass

    return _P


class TestPetPaceMatching:
    def test_matches_exact_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name=PETPACE_NAME))) == 1

    def test_name_match_is_case_sensitive(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="collar")) == []

    def test_no_match_on_longer_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Collar 42")) == []
        assert registry.match(_make_ad(local_name="DogCollar")) == []

    def test_service_uuid_alone_is_not_a_match(self):
        # 0xFE50 is SIG-assigned to Google and shared by many products, so it
        # is never a match criterion on its own.
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(service_uuids=[PETPACE_SERVICE_UUID])) == []


class TestPetPaceParsing:
    def test_basics(self):
        result = PetPaceParser().parse(_make_ad(local_name=PETPACE_NAME))
        assert result is not None
        assert result.parser_name == "petpace"
        assert result.beacon_type == "petpace"
        assert result.device_class == "pet_tracker"
        assert result.metadata["vendor"] == "PetPace"
        assert result.metadata["model"] == "PetPace Smart Collar"

    def test_confidence_low_without_service_uuid(self):
        result = PetPaceParser().parse(_make_ad(local_name=PETPACE_NAME))
        assert result.metadata["confidence"] == "low"
        assert result.metadata["has_petpace_service"] is False

    def test_confidence_high_with_service_uuid(self):
        result = PetPaceParser().parse(
            _make_ad(local_name=PETPACE_NAME, service_uuids=["fe50"])
        )
        assert result.metadata["confidence"] == "high"
        assert result.metadata["has_petpace_service"] is True

    def test_full_service_uuid_form_recognised(self):
        result = PetPaceParser().parse(
            _make_ad(local_name=PETPACE_NAME, service_uuids=[PETPACE_SERVICE_UUID])
        )
        assert result.metadata["has_petpace_service"] is True

    def test_no_telemetry_in_advert(self):
        # Vitals require a GATT connection; nothing is broadcast.
        result = PetPaceParser().parse(_make_ad(local_name=PETPACE_NAME))
        assert result.metadata["telemetry_in_advert"] is False

    def test_identity_hash_is_mac_based(self):
        # The name is identical on every collar -- the MAC is the only
        # passive discriminator.
        result = PetPaceParser().parse(_make_ad(local_name=PETPACE_NAME))
        expected = hashlib.sha256(b"petpace:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_on_other_names(self):
        assert PetPaceParser().parse(_make_ad(local_name="collar")) is None
        assert PetPaceParser().parse(_make_ad(local_name="Collar 42")) is None
        assert PetPaceParser().parse(_make_ad()) is None
