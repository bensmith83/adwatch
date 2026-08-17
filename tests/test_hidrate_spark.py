"""Tests for the HidrateSpark smart water bottle plugin.

Source: apk-ble-hunting/reports/hidratenow-hidrate_passive.md. The bottle
broadcasts no manufacturer data, no service data and no telemetry -- the
entire passive surface is the advertised name ``h2o<serial>``, where the
serial is the GATT Serial Number broadcast in the clear and non-rotating
(`RxBLEBottleConnectionManager.java:2521`, `:2551`, `:2920`).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.hidrate_spark import (
    HidrateSparkParser,
    HIDRATE_NAME_PATTERN,
    extract_serial,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _registry():
    registry = ParserRegistry()

    @register_parser(
        name="hidrate_spark",
        local_name_pattern=HIDRATE_NAME_PATTERN,
        description="HidrateSpark",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(HidrateSparkParser):
        pass

    return registry


class TestSerialExtraction:
    def test_strips_h2o_prefix(self):
        assert extract_serial("h2o1A2B3C") == "1A2B3C"

    def test_case_insensitive_prefix(self):
        assert extract_serial("H2O1A2B3C") == "1A2B3C"

    def test_returns_none_without_prefix(self):
        assert extract_serial("Spark1A2B") is None

    def test_returns_none_for_bare_prefix(self):
        assert extract_serial("h2o") is None


class TestHidrateMatching:
    @pytest.mark.parametrize("name", ["h2o1A2B3C", "H2O998877", "h2oABCDEF12"])
    def test_matches_bottle_names(self, name):
        assert len(_registry().match(_make_ad(local_name=name))) == 1

    @pytest.mark.parametrize("name", [
        "h2o",            # no serial tail
        "h2o1",           # too short to be a serial
        "MyH2O Sensor",   # substring, not the documented prefix form
        "Spark Bottle",
        None,
    ])
    def test_does_not_match(self, name):
        assert _registry().match(_make_ad(local_name=name)) == []

    def test_parse_rejects_non_bottle(self):
        assert HidrateSparkParser().parse(_make_ad(local_name="Spark Bottle")) is None

    def test_parse_rejects_missing_name(self):
        assert HidrateSparkParser().parse(_make_ad(local_name=None)) is None


class TestHidrateMetadata:
    def test_core_fields(self):
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        assert result is not None
        assert result.parser_name == "hidrate_spark"
        assert result.beacon_type == "hidrate_spark"
        assert result.device_class == "bottle"
        assert result.metadata["vendor"] == "Hidrate"
        assert result.metadata["model"] == "HidrateSpark"
        assert result.metadata["serial_number"] == "1A2B3C"
        assert result.metadata["device_name"] == "h2o1A2B3C"

    def test_flags_persistent_identifier(self):
        """The serial never rotates -- flag it as a trackability signal."""
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        assert result.metadata["persistent_identifier"] is True

    def test_no_passive_telemetry_flag(self):
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        assert result.metadata["passive_telemetry"] is False

    def test_raw_payload_is_empty(self):
        """No manufacturer data and no service data are broadcast."""
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        assert result.raw_payload_hex == ""


class TestHidrateIdentity:
    def test_identity_hash_from_serial(self):
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        expected = hashlib.sha256(b"hidrate_spark:1A2B3C").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_mac(self):
        a = HidrateSparkParser().parse(
            _make_ad(local_name="h2o1A2B3C", mac_address="AA:BB:CC:DD:EE:FF"))
        b = HidrateSparkParser().parse(
            _make_ad(local_name="h2o1A2B3C", mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash == b.identifier_hash

    def test_identity_differs_per_serial(self):
        a = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        b = HidrateSparkParser().parse(_make_ad(local_name="h2o998877"))
        assert a.identifier_hash != b.identifier_hash

    def test_identity_hash_length(self):
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_stable_key_is_the_serial(self):
        """Name-only ad never varies, so the serial is the dedup key."""
        result = HidrateSparkParser().parse(_make_ad(local_name="h2o1A2B3C"))
        assert result.stable_key == "hidrate_spark:1A2B3C"
