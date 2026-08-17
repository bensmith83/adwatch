"""Tests for the Neurovalens Modius neurostimulation plugin.

Per apk-ble-hunting/reports/neurovalens-modius_passive.md — the GAP device name
is the *only* discriminator; the three product variants are byte-identical on
air except for the ASCII name.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.modius import ModiusParser, MODIUS_NAME_PATTERN


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "EC:1B:BD:11:22:33",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="modius",
        local_name_pattern=MODIUS_NAME_PATTERN,
        description="Modius",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ModiusParser):
        pass

    return _P


class TestModiusMatching:
    def test_matches_sleep(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Sleep"))) == 1

    def test_matches_modius_legacy(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Modius"))) == 1

    def test_matches_bootloader_suffix(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="StressBL"))) == 1

    def test_does_not_match_longer_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Sleep Number Bed")) == []

    def test_does_not_match_sleeptracker(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="SleepTracker")) == []


class TestModiusParsing:
    def test_parses_sleep_variant(self):
        result = ModiusParser().parse(_make_ad(local_name="Sleep"))
        assert result is not None
        assert result.parser_name == "modius"
        assert result.beacon_type == "modius"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Neurovalens"
        assert result.metadata["product_variant"] == "Modius Sleep"
        assert result.metadata["firmware_generation"] == "V2"

    def test_parses_stress_variant(self):
        result = ModiusParser().parse(_make_ad(local_name="Stress"))
        assert result.metadata["product_variant"] == "Modius Stress"
        assert result.metadata["firmware_generation"] == "V2"

    def test_parses_slim_variant(self):
        result = ModiusParser().parse(_make_ad(local_name="Slim"))
        assert result.metadata["product_variant"] == "Modius Slim"
        assert result.metadata["firmware_generation"] == "V2"

    def test_legacy_modius_maps_to_slim_v1(self):
        result = ModiusParser().parse(_make_ad(local_name="Modius"))
        assert result.metadata["product_variant"] == "Modius Slim"
        assert result.metadata["firmware_generation"] == "V1"

    def test_vestal_maps_to_slim_v1(self):
        result = ModiusParser().parse(_make_ad(local_name="VESTAL"))
        assert result.metadata["product_variant"] == "Modius Slim"
        assert result.metadata["firmware_generation"] == "V1"

    def test_name_match_is_case_insensitive(self):
        result = ModiusParser().parse(_make_ad(local_name="sLeEp"))
        assert result.metadata["product_variant"] == "Modius Sleep"

    def test_bootloader_mode_flagged(self):
        result = ModiusParser().parse(_make_ad(local_name="SleepB"))
        assert result.metadata["bootloader_mode"] is True
        assert result.metadata["product_variant"] == "Modius Sleep"

    def test_bootloader_bl_suffix(self):
        result = ModiusParser().parse(_make_ad(local_name="ModiusBL"))
        assert result.metadata["bootloader_mode"] is True

    def test_normal_mode_not_flagged(self):
        result = ModiusParser().parse(_make_ad(local_name="Sleep"))
        assert result.metadata["bootloader_mode"] is False

    def test_generic_word_names_are_lower_confidence(self):
        """`Sleep`/`Stress`/`Slim` are ordinary English words."""
        assert ModiusParser().parse(_make_ad(local_name="Sleep")).metadata[
            "confidence"] == "medium"
        assert ModiusParser().parse(_make_ad(local_name="Modius")).metadata[
            "confidence"] == "high"

    def test_flags_sensitive_category(self):
        result = ModiusParser().parse(_make_ad(local_name="Sleep"))
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "neurostimulation"

    def test_no_telemetry_claimed(self):
        result = ModiusParser().parse(_make_ad(local_name="Sleep"))
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_identity_hash_from_mac(self):
        result = ModiusParser().parse(_make_ad(local_name="Sleep"))
        expected = hashlib.sha256(b"modius:EC:1B:BD:11:22:33").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_bootloader_mode(self):
        a = ModiusParser().parse(_make_ad(local_name="Sleep"))
        b = ModiusParser().parse(_make_ad(local_name="SleepB"))
        assert a.identifier_hash == b.identifier_hash

    def test_rejects_unrelated_name(self):
        assert ModiusParser().parse(_make_ad(local_name="Slimline")) is None

    def test_rejects_missing_name(self):
        assert ModiusParser().parse(_make_ad(local_name=None)) is None

    def test_storage_schema_is_none(self):
        assert ModiusParser().storage_schema() is None
