"""Tests for the Petkit pet-gadget plugin.

Source: apk-ble-hunting/reports/petkit-oversea_passive.md — discovery is a
case-insensitive *equality* match against seven exact local-name strings;
all products share the `0000aaa0-` GATT service.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.petkit import (
    PetkitParser,
    PETKIT_NAME_PATTERN,
    PETKIT_SERVICE_UUID,
    PETKIT_MODELS,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="petkit",
        local_name_pattern=PETKIT_NAME_PATTERN,
        description="Petkit",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PetkitParser):
        pass

    return _P


class TestPetkitMatching:
    @pytest.mark.parametrize(
        "name", ["PETKIT", "PETKIT2", "Fit P1", "Fit P2", "pethome", "petmate", "petGO"]
    )
    def test_matches_each_filter_name(self, name):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name=name))) == 1

    def test_match_is_case_insensitive(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="petkit2"))) == 1

    def test_no_match_on_prefix_only(self):
        # Petkit uses equalsIgnoreCase, not startsWith -- a longer name is a
        # different device.
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="PETKITTY")) == []

    def test_no_match_unrelated_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Fit Pro")) == []


class TestPetkitParsing:
    def test_basics(self):
        result = PetkitParser().parse(_make_ad(local_name="PETKIT2"))
        assert result is not None
        assert result.parser_name == "petkit"
        assert result.beacon_type == "petkit"
        assert result.device_class == "pet_tracker"
        assert result.metadata["vendor"] == "Petkit"

    @pytest.mark.parametrize(
        "name,model",
        [
            ("PETKIT", "Fit P1"),
            ("Fit P1", "Fit P1"),
            ("PETKIT2", "Fit P2"),
            ("Fit P2", "Fit P2"),
            ("pethome", "PetHome"),
            ("petmate", "PetMate"),
            ("petGO", "petGO"),
        ],
    )
    def test_model_mapping(self, name, model):
        result = PetkitParser().parse(_make_ad(local_name=name))
        assert result.metadata["model"] == model

    def test_model_mapping_case_insensitive(self):
        result = PetkitParser().parse(_make_ad(local_name="FIT P2"))
        assert result.metadata["model"] == "Fit P2"

    def test_advertised_name_preserved(self):
        result = PetkitParser().parse(_make_ad(local_name="petGO"))
        assert result.metadata["device_name"] == "petGO"

    def test_models_table_covers_every_filter_name(self):
        assert set(PETKIT_MODELS) == {
            "petkit", "petkit2", "fit p1", "fit p2", "pethome", "petmate", "petgo"
        }

    def test_shared_service_uuid_flagged(self):
        result = PetkitParser().parse(
            _make_ad(local_name="PETKIT", service_uuids=[PETKIT_SERVICE_UUID])
        )
        assert result.metadata["has_petkit_service"] is True

    def test_service_uuid_absent_flag_false(self):
        result = PetkitParser().parse(_make_ad(local_name="PETKIT"))
        assert result.metadata["has_petkit_service"] is False

    def test_service_uuid_alone_does_not_classify(self):
        # 0000aaa0 is a SIG-base squat used by several OEMs; the name is the
        # authoritative signal.
        assert PetkitParser().parse(_make_ad(service_uuids=[PETKIT_SERVICE_UUID])) is None

    def test_identity_hash_is_mac_based(self):
        # The name is shared across every unit of a SKU, so the MAC is the
        # only per-unit discriminator.
        result = PetkitParser().parse(_make_ad(local_name="PETKIT2"))
        expected = hashlib.sha256(b"petkit:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_without_name(self):
        assert PetkitParser().parse(_make_ad()) is None
