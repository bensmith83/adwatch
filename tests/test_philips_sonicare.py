"""Tests for Philips Sonicare toothbrush BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.philips_sonicare import (
    PhilipsSonicareParser,
    SONICARE_UUID,
    SONICARE_NAME_RE,
)


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
        name="philips_sonicare",
        service_uuid=SONICARE_UUID,
        local_name_pattern=r"Sonicare",
        description="Philips Sonicare toothbrush advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(PhilipsSonicareParser):
        pass

    return registry


class TestPhilipsSonicareParser:
    def test_matches_service_uuid(self):
        """Matches on Sonicare service UUID."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=[SONICARE_UUID])
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name containing 'Sonicare'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Sonicare DiamondClean")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_parse_with_uuid_match(self):
        """Parses successfully when service UUID matches."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=[SONICARE_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "philips_sonicare"
        assert result.beacon_type == "philips_sonicare"
        assert result.device_class == "personal_care"

    def test_parse_with_name_match(self):
        """Parses successfully when local_name contains 'Sonicare'."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(local_name="Sonicare DiamondClean")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "philips_sonicare"

    def test_parse_with_both_uuid_and_name(self):
        """Parses successfully when both UUID and name match."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(
            service_uuids=[SONICARE_UUID],
            local_name="Sonicare DiamondClean",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_name"] == "Sonicare DiamondClean"

    def test_metadata_device_name_from_local_name(self):
        """metadata includes device_name when local_name is set."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(
            service_uuids=[SONICARE_UUID],
            local_name="Sonicare 9900 Prestige",
        )
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Sonicare 9900 Prestige"

    def test_metadata_no_device_name_when_no_local_name(self):
        """metadata has no device_name when local_name is None."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=[SONICARE_UUID])
        result = parser.parse(ad)
        assert "device_name" not in result.metadata

    def test_identity_hash_format(self):
        """Identity hash is SHA256('philips_sonicare:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=[SONICARE_UUID], mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"philips_sonicare:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_differs_by_mac(self):
        """Different MAC addresses produce different identity hashes."""
        parser = PhilipsSonicareParser()
        ad1 = _make_ad(service_uuids=[SONICARE_UUID], mac_address="AA:BB:CC:DD:EE:01")
        ad2 = _make_ad(service_uuids=[SONICARE_UUID], mac_address="AA:BB:CC:DD:EE:02")
        r1 = parser.parse(ad1)
        r2 = parser.parse(ad2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_raw_payload_hex_is_empty(self):
        """raw_payload_hex is empty string (no payload parsing)."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=[SONICARE_UUID])
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_returns_none_no_uuid_no_name(self):
        """Returns None when neither UUID nor name matches."""
        parser = PhilipsSonicareParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_wrong_uuid(self):
        """Returns None for a different service UUID."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=["00001800-0000-1000-8000-00805f9b34fb"])
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_non_matching_name(self):
        """Returns None when local_name doesn't contain 'Sonicare'."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(local_name="OralB SmartSeries")
        result = parser.parse(ad)
        assert result is None

    def test_name_match_is_substring(self):
        """Name match works as substring search (not just prefix)."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(local_name="Philips Sonicare 9900")
        result = parser.parse(ad)
        assert result is not None

    def test_empty_service_uuids_no_name(self):
        """Returns None with empty service_uuids list and no name."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=[])
        result = parser.parse(ad)
        assert result is None

    def test_device_class_is_personal_care(self):
        """device_class is always 'personal_care'."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(local_name="Sonicare")
        result = parser.parse(ad)
        assert result.device_class == "personal_care"

    def test_beacon_type(self):
        """beacon_type is 'philips_sonicare'."""
        parser = PhilipsSonicareParser()
        ad = _make_ad(service_uuids=[SONICARE_UUID])
        result = parser.parse(ad)
        assert result.beacon_type == "philips_sonicare"
