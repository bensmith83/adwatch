"""Tests for UniFi Protect BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.unifi_protect import UniFiProtectParser, UNIFI_UUID


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
        name="unifi_protect",
        service_uuid=UNIFI_UUID,
        local_name_pattern=r"^UCK",
        description="UniFi Protect camera advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(UniFiProtectParser):
        pass

    return registry


class TestUniFiProtectParser:
    def test_matches_service_uuid(self):
        """Matches on UniFi Protect service UUID."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=[UNIFI_UUID])
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name starting with UCK."""
        registry = _make_registry()
        ad = _make_ad(local_name="UCK-G2-Plus")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_parse_with_service_uuid(self):
        """Parses ad matched by service UUID."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "unifi_protect"
        assert result.beacon_type == "unifi_protect"
        assert result.device_class == "camera"

    def test_parse_with_local_name(self):
        """Parses ad matched by local_name pattern."""
        parser = UniFiProtectParser()
        ad = _make_ad(local_name="UCK-G2-Plus")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "unifi_protect"
        assert result.device_class == "camera"

    def test_parse_with_both_uuid_and_name(self):
        """Parses ad with both service UUID and matching local_name."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID], local_name="UCK-G2-Plus")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_name"] == "UCK-G2-Plus"

    def test_device_name_in_metadata(self):
        """local_name is stored as device_name in metadata."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID], local_name="UCK-G4-Pro")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "UCK-G4-Pro"

    def test_no_device_name_when_no_local_name(self):
        """device_name not in metadata when local_name is None."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID])
        result = parser.parse(ad)
        assert "device_name" not in result.metadata

    def test_identity_hash_format(self):
        """Identity hash is SHA256('unifi_protect:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID], mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"unifi_protect:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_stable(self):
        """Same MAC always produces same identity hash."""
        parser = UniFiProtectParser()
        ad1 = _make_ad(service_uuids=[UNIFI_UUID], mac_address="AA:BB:CC:DD:EE:FF")
        ad2 = _make_ad(service_uuids=[UNIFI_UUID], mac_address="AA:BB:CC:DD:EE:FF")
        r1 = parser.parse(ad1)
        r2 = parser.parse(ad2)
        assert r1.identifier_hash == r2.identifier_hash

    def test_identity_hash_differs_by_mac(self):
        """Different MACs produce different identity hashes."""
        parser = UniFiProtectParser()
        ad1 = _make_ad(service_uuids=[UNIFI_UUID], mac_address="11:11:11:11:11:11")
        ad2 = _make_ad(service_uuids=[UNIFI_UUID], mac_address="22:22:22:22:22:22")
        r1 = parser.parse(ad1)
        r2 = parser.parse(ad2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_returns_none_no_uuid_no_name(self):
        """Returns None when neither UUID nor name matches."""
        parser = UniFiProtectParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_wrong_uuid(self):
        """Returns None for a different service UUID."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=["00001234-0000-1000-8000-00805f9b34fb"])
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_non_matching_name(self):
        """Returns None when local_name doesn't start with UCK."""
        parser = UniFiProtectParser()
        ad = _make_ad(local_name="SomeOtherDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_name_contains_uck_not_prefix(self):
        """Returns None when UCK appears mid-string (not prefix)."""
        parser = UniFiProtectParser()
        ad = _make_ad(local_name="MyUCK-Device")
        result = parser.parse(ad)
        assert result is None

    def test_raw_payload_hex_is_empty(self):
        """raw_payload_hex is empty string (no manufacturer data parsed)."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID])
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_beacon_type(self):
        """beacon_type is 'unifi_protect'."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[UNIFI_UUID])
        result = parser.parse(ad)
        assert result.beacon_type == "unifi_protect"

    def test_device_class_is_camera(self):
        """device_class is always 'camera'."""
        parser = UniFiProtectParser()
        ad = _make_ad(local_name="UCK-G2-Bullet")
        result = parser.parse(ad)
        assert result.device_class == "camera"

    def test_empty_service_uuids_list(self):
        """Returns None when service_uuids is empty list and no name match."""
        parser = UniFiProtectParser()
        ad = _make_ad(service_uuids=[])
        result = parser.parse(ad)
        assert result is None

    def test_registry_match_and_parse(self):
        """End-to-end: registry match + parse returns correct result."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=[UNIFI_UUID], local_name="UCK-G4-Doorbell")
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "unifi_protect"
        assert result.metadata["device_name"] == "UCK-G4-Doorbell"
        assert result.device_class == "camera"
