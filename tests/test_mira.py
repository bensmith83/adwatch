"""Tests for the Mira hormone/fertility analyzer plugin.

Per apk-ble-hunting/reports/mira-fertilitytracker-android-us_passive.md —
name-only discovery on the exact literals ``Mira-Analyzer`` and ``EVA3000``.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.mira import MiraParser, MIRA_NAME_PATTERN


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "DC:0D:30:AA:BB:CC",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="mira",
        local_name_pattern=MIRA_NAME_PATTERN,
        description="Mira",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(MiraParser):
        pass

    return _P


class TestMiraMatching:
    def test_matches_mira_analyzer(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Mira-Analyzer"))) == 1

    def test_matches_eva3000(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="EVA3000"))) == 1

    def test_does_not_match_prefix_superstring(self):
        """The app filters on exact names, not prefixes."""
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Mira-Analyzer-Pro")) == []

    def test_does_not_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="EVA")) == []


class TestMiraParsing:
    def test_parses_analyzer(self):
        result = MiraParser().parse(_make_ad(local_name="Mira-Analyzer"))
        assert result is not None
        assert result.parser_name == "mira"
        assert result.beacon_type == "mira"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Mira"
        assert result.metadata["model"] == "Mira-Analyzer"
        assert result.metadata["device_name"] == "Mira-Analyzer"

    def test_parses_eva3000_model(self):
        result = MiraParser().parse(_make_ad(local_name="EVA3000"))
        assert result.metadata["model"] == "EVA3000"

    def test_flags_sensitive_category(self):
        result = MiraParser().parse(_make_ad(local_name="Mira-Analyzer"))
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "reproductive_health"

    def test_no_telemetry_claimed(self):
        result = MiraParser().parse(_make_ad(local_name="EVA3000"))
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_identity_hash_from_mac(self):
        result = MiraParser().parse(_make_ad(local_name="Mira-Analyzer"))
        expected = hashlib.sha256(b"mira:DC:0D:30:AA:BB:CC").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_models(self):
        a = MiraParser().parse(_make_ad(local_name="Mira-Analyzer"))
        b = MiraParser().parse(_make_ad(local_name="EVA3000"))
        assert a.identifier_hash == b.identifier_hash

    def test_rejects_partial_name(self):
        assert MiraParser().parse(_make_ad(local_name="Mira")) is None

    def test_rejects_missing_name(self):
        assert MiraParser().parse(_make_ad(local_name=None)) is None

    def test_rejects_uuid_only_ad(self):
        ad = _make_ad(service_uuids=["0000fff0-0000-1000-8000-00805f9b34fb"])
        assert MiraParser().parse(ad) is None

    def test_storage_schema_is_none(self):
        assert MiraParser().storage_schema() is None
