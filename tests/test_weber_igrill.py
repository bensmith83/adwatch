"""Tests for Weber iGrill BLE thermometer plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.weber_igrill import WeberIGrillParser


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="weber_igrill",
        local_name_pattern=r"(?i)igrill",
        description="Weber iGrill thermometer advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(WeberIGrillParser):
        pass

    return registry


class TestWeberIGrillRegistry:
    def test_matches_local_name_igrill2(self):
        """Matches on local_name containing 'iGrill'."""
        registry = _make_registry()
        ad = _make_ad(local_name="iGrill2_12345")
        matches = registry.match(ad)
        assert len(matches) >= 1


class TestWeberIGrillParser:
    def test_parser_name(self):
        """parser_name is 'weber_igrill'."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.parser_name == "weber_igrill"

    def test_beacon_type(self):
        """beacon_type is 'weber_igrill'."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.beacon_type == "weber_igrill"

    def test_device_class_thermometer(self):
        """device_class is 'thermometer'."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.device_class == "thermometer"

    # --- Model detection from local_name ---

    def test_model_igrill_mini(self):
        """iGrill_mini_12345 -> model='iGrill Mini', probes=1."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill_mini_12345")
        result = parser.parse(ad)
        assert result.metadata["model"] == "iGrill Mini"
        assert result.metadata["probes"] == 1

    def test_model_igrill2(self):
        """iGrill2_12345 -> model='iGrill 2', probes=4."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.metadata["model"] == "iGrill 2"
        assert result.metadata["probes"] == 4

    def test_model_igrill3(self):
        """iGrill3_67890 -> model='iGrill 3', probes=4."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill3_67890")
        result = parser.parse(ad)
        assert result.metadata["model"] == "iGrill 3"
        assert result.metadata["probes"] == 4

    def test_model_unknown_variant(self):
        """iGrill_unknown -> model='iGrill Unknown', probes=4."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill_unknown")
        result = parser.parse(ad)
        assert result.metadata["model"] == "iGrill Unknown"
        assert result.metadata["probes"] == 4

    # --- Device ID extraction ---

    def test_device_id_from_local_name(self):
        """iGrill2_12345 -> device_id='12345'."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "12345"

    def test_device_id_missing_no_underscore_suffix(self):
        """iGrill2 (no underscore suffix) -> device_id not present or None."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2")
        result = parser.parse(ad)
        assert result.metadata.get("device_id") is None

    # --- local_name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to the raw local_name."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "iGrill2_12345"

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac:weber_igrill)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:weber_igrill".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex_with_manufacturer_data(self):
        """raw_payload_hex is hex of manufacturer payload if present."""
        parser = WeberIGrillParser()
        mfr_data = b"\x01\x02\xDE\xAD\xBE\xEF"
        ad = _make_ad(local_name="iGrill2_12345", manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr_data.hex()

    def test_raw_payload_hex_empty_without_manufacturer_data(self):
        """raw_payload_hex is '' when no manufacturer_data."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    # --- Edge cases ---

    def test_returns_none_for_none_local_name(self):
        """Returns None when local_name is None."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name=None)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_non_igrill_local_name(self):
        """Returns None for local_name that doesn't contain 'igrill'."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="SomeOtherDevice")
        result = parser.parse(ad)
        assert result is None

    def test_works_without_manufacturer_data(self):
        """Returns valid result with no manufacturer_data."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="iGrill2_12345")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "weber_igrill"
        assert result.raw_payload_hex == ""

    def test_case_insensitive_matching(self):
        """Case insensitive: IGRILL2_ABC still matches."""
        parser = WeberIGrillParser()
        ad = _make_ad(local_name="IGRILL2_ABC")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "weber_igrill"
