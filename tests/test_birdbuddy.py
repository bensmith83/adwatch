"""Tests for the Bird Buddy smart bird-feeder plugin.

Source: apk-ble-hunting/reports/birdbuddy-app_passive.md (filters recovered
from the Hermes bytecode via droidsaw).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.birdbuddy import (
    BirdBuddyParser,
    BIRDBUDDY_NAME_PATTERN,
    BIRDBUDDY_V1_UUID,
    BIRDBUDDY_V2_UUID,
    BIRDBUDDY_WEAK_UUIDS,
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
        name="birdbuddy",
        service_uuid=[BIRDBUDDY_V1_UUID, BIRDBUDDY_V2_UUID],
        local_name_pattern=BIRDBUDDY_NAME_PATTERN,
        description="Bird Buddy",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(BirdBuddyParser):
        pass

    return _P


class TestBirdBuddyMatching:
    def test_matches_v1_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[BIRDBUDDY_V1_UUID]))) == 1

    def test_matches_v2_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[BIRDBUDDY_V2_UUID]))) == 1

    @pytest.mark.parametrize("name", ["BbBUDDY", "Bb1234BUDDY", "BUDDY-0001"])
    def test_matches_name_shapes(self, name):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name=name))) == 1

    def test_name_match_is_case_sensitive(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Bbbuddy")) == []

    def test_no_match_on_embedded_buddy(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="MyBUDDY Speaker")) == []

    def test_weak_uuids_not_registered(self):
        # 0000ff01 is generic and 0000a00a is already claimed by meross, so
        # neither may be a match criterion.
        registry = ParserRegistry()
        _register(registry)
        for uuid in BIRDBUDDY_WEAK_UUIDS:
            assert registry.match(_make_ad(service_uuids=[uuid])) == []


class TestBirdBuddyParsing:
    def test_basics(self):
        result = BirdBuddyParser().parse(_make_ad(local_name="BbBUDDY"))
        assert result is not None
        assert result.parser_name == "birdbuddy"
        assert result.beacon_type == "birdbuddy"
        assert result.device_class == "camera"
        assert result.metadata["vendor"] == "Bird Buddy"

    def test_v1_hardware_revision(self):
        result = BirdBuddyParser().parse(
            _make_ad(service_uuids=[BIRDBUDDY_V1_UUID], local_name="BbBUDDY"))
        assert result.metadata["hardware_revision"] == "V1"

    def test_v2_hardware_revision(self):
        result = BirdBuddyParser().parse(
            _make_ad(service_uuids=[BIRDBUDDY_V2_UUID], local_name="BbBUDDY"))
        assert result.metadata["hardware_revision"] == "V2"

    def test_uuid_only_yields_to_amazon_freertos(self):
        # The two UUIDs are AmazonFreeRTOS SDK services shared with Pentair
        # and any other AFR device; without the Bird Buddy name the sighting
        # belongs to plugins/amazon_freertos.py, not to us.
        assert BirdBuddyParser().parse(_make_ad(service_uuids=[BIRDBUDDY_V1_UUID])) is None
        assert BirdBuddyParser().parse(_make_ad(service_uuids=[BIRDBUDDY_V2_UUID])) is None

    def test_name_only_revision_unknown(self):
        result = BirdBuddyParser().parse(_make_ad(local_name="BbBUDDY"))
        assert result.metadata["hardware_revision"] == "unknown"

    def test_bb_prefix_stripped_for_display(self):
        result = BirdBuddyParser().parse(_make_ad(local_name="Bb1234BUDDY"))
        assert result.metadata["display_name"] == "1234BUDDY"

    def test_display_name_unchanged_without_prefix(self):
        result = BirdBuddyParser().parse(_make_ad(local_name="BUDDY-0001"))
        assert result.metadata["display_name"] == "BUDDY-0001"

    def test_weak_uuid_recorded_when_paired_with_a_real_signal(self):
        result = BirdBuddyParser().parse(
            _make_ad(local_name="BbBUDDY", service_uuids=["ff01"])
        )
        assert result.metadata["weak_uuid_hits"] == ["0000ff01-0000-1000-8000-00805f9b34fb"]

    def test_setup_mode_flag(self):
        # BLE is onboarding-only; a broadcasting feeder is mid-setup.
        result = BirdBuddyParser().parse(_make_ad(local_name="BbBUDDY"))
        assert result.metadata["setup_mode"] is True

    def test_identity_hash_is_mac_based(self):
        result = BirdBuddyParser().parse(_make_ad(local_name="BbBUDDY"))
        expected = hashlib.sha256(b"birdbuddy:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert BirdBuddyParser().parse(_make_ad(local_name="Bbbuddy")) is None
        assert BirdBuddyParser().parse(_make_ad(service_uuids=["ff01"])) is None
        assert BirdBuddyParser().parse(_make_ad()) is None
