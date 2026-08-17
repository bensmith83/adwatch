"""Tests for the Perifit pelvic-floor biofeedback probe plugin.

Per apk-ble-hunting/reports/starshipproduct-perifitmainapp_passive.md —
name-prefix-only discovery, case-insensitive, tolerating NUL padding.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.perifit import PerifitParser, PERIFIT_NAME_PATTERN


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "F0:C7:7F:01:02:03",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="perifit",
        local_name_pattern=PERIFIT_NAME_PATTERN,
        description="Perifit",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PerifitParser):
        pass

    return _P


class TestPerifitMatching:
    def test_matches_perifit(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Perifit"))) == 1

    def test_matches_case_insensitively(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="PERIFIT 2A"))) == 1

    def test_matches_urgo_rebrand(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Urgo Femme"))) == 1

    def test_matches_urg_zero_variant(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Urg0"))) == 1

    def test_matches_name_with_unit_suffix(self):
        """The app uses startsWith, so a per-unit suffix must still match."""
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Perifit1234"))) == 1

    def test_does_not_match_generic_devkit_name(self):
        """`SimpleBLE` is an eval-kit default — too generic to claim."""
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="SimpleBLEPeripheral")) == []

    def test_does_not_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Urgent Care Beacon")) == []


class TestPerifitParsing:
    def test_parses_presence(self):
        result = PerifitParser().parse(_make_ad(local_name="Perifit 2A"))
        assert result is not None
        assert result.parser_name == "perifit"
        assert result.beacon_type == "perifit"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Perifit"
        assert result.metadata["device_name"] == "Perifit 2A"

    def test_brand_variant_perifit(self):
        result = PerifitParser().parse(_make_ad(local_name="perifit"))
        assert result.metadata["brand_variant"] == "Perifit"

    def test_brand_variant_urgo(self):
        result = PerifitParser().parse(_make_ad(local_name="URGO"))
        assert result.metadata["brand_variant"] == "Urgo (OEM rebrand)"

    def test_rejects_urgo_prefix_continued_by_letters(self):
        """`Urgo` is short; only accept it as a whole word or with a
        non-alphabetic suffix, so `Urgonomics` is not an Urgo probe."""
        assert PerifitParser().parse(_make_ad(local_name="Urgonomics")) is None

    def test_accepts_urgo_with_numeric_suffix(self):
        result = PerifitParser().parse(_make_ad(local_name="Urgo01"))
        assert result is not None
        assert result.metadata["brand_variant"] == "Urgo (OEM rebrand)"

    def test_strips_nul_padding_from_name(self):
        result = PerifitParser().parse(_make_ad(local_name="Perifit\x00\x00"))
        assert result is not None
        assert result.metadata["device_name"] == "Perifit"

    def test_flags_sensitive_category(self):
        result = PerifitParser().parse(_make_ad(local_name="Perifit"))
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "reproductive_health"

    def test_no_telemetry_claimed(self):
        result = PerifitParser().parse(_make_ad(local_name="Perifit"))
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_identity_hash_from_mac(self):
        result = PerifitParser().parse(_make_ad(local_name="Perifit"))
        expected = hashlib.sha256(b"perifit:F0:C7:7F:01:02:03").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_rejects_unrelated_name(self):
        assert PerifitParser().parse(_make_ad(local_name="Elvie Pump")) is None

    def test_rejects_missing_name(self):
        assert PerifitParser().parse(_make_ad(local_name=None)) is None

    def test_rejects_empty_name(self):
        assert PerifitParser().parse(_make_ad(local_name="")) is None

    def test_storage_schema_is_none(self):
        assert PerifitParser().storage_schema() is None
