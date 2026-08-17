"""Tests for the Tempdrop BBT wearable plugin.

Per apk-ble-hunting/reports/tempdrop-tempdropmobileapp_passive.md — a
presence-only beacon discovered by the local-name prefix ``Tempdrop ``
(optionally corroborated by service UUID 0xF000).
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tempdrop import (
    TempdropParser,
    TEMPDROP_NAME_PATTERN,
    TEMPDROP_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "C4:BE:84:11:22:33",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="tempdrop",
        local_name_pattern=TEMPDROP_NAME_PATTERN,
        description="Tempdrop",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(TempdropParser):
        pass

    return _P


class TestTempdropMatching:
    def test_matches_name_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Tempdrop A1B2")
        assert len(registry.match(ad)) == 1

    def test_matches_bare_prefix_with_trailing_space(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Tempdrop ")
        assert len(registry.match(ad)) == 1

    def test_does_not_match_other_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="TempoDrop Sensor")
        assert registry.match(ad) == []

    def test_does_not_register_bare_f000_uuid(self):
        """0xF000 is a generic TI service base — must not match on its own."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TEMPDROP_SERVICE_UUID])
        assert registry.match(ad) == []


class TestTempdropParsing:
    def test_parses_presence(self):
        result = TempdropParser().parse(_make_ad(local_name="Tempdrop 4F21"))
        assert result is not None
        assert result.parser_name == "tempdrop"
        assert result.beacon_type == "tempdrop"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Tempdrop"
        assert result.metadata["product"] == "Tempdrop BBT wearable"
        assert result.metadata["device_name"] == "Tempdrop 4F21"

    def test_flags_sensitive_category(self):
        result = TempdropParser().parse(_make_ad(local_name="Tempdrop 4F21"))
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "reproductive_health"

    def test_confidence_high_with_service_uuid(self):
        ad = _make_ad(
            local_name="Tempdrop 4F21",
            service_uuids=["0000f000-0000-1000-8000-00805f9b34fb"],
        )
        result = TempdropParser().parse(ad)
        assert result.metadata["confidence"] == "high"
        assert result.metadata["service_uuid_seen"] is True

    def test_confidence_medium_without_service_uuid(self):
        result = TempdropParser().parse(_make_ad(local_name="Tempdrop 4F21"))
        assert result.metadata["confidence"] == "medium"
        assert result.metadata["service_uuid_seen"] is False

    def test_no_telemetry_claimed(self):
        """Report is explicit: nothing but presence is broadcast."""
        result = TempdropParser().parse(_make_ad(local_name="Tempdrop 4F21"))
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_identity_hash_from_mac(self):
        ad = _make_ad(local_name="Tempdrop 4F21")
        result = TempdropParser().parse(ad)
        expected = hashlib.sha256(
            b"tempdrop:C4:BE:84:11:22:33"
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_name_suffix(self):
        a = TempdropParser().parse(_make_ad(local_name="Tempdrop A"))
        b = TempdropParser().parse(_make_ad(local_name="Tempdrop B"))
        assert a.identifier_hash == b.identifier_hash

    def test_rejects_non_tempdrop(self):
        assert TempdropParser().parse(_make_ad(local_name="Polar H10")) is None

    def test_rejects_missing_name(self):
        assert TempdropParser().parse(_make_ad(local_name=None)) is None

    def test_rejects_uuid_only(self):
        ad = _make_ad(service_uuids=["0000f000-0000-1000-8000-00805f9b34fb"])
        assert TempdropParser().parse(ad) is None

    def test_storage_schema_is_none(self):
        assert TempdropParser().storage_schema() is None
