"""Tests for Raven gunshot detector (SoundThinking) plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.raven_gunshot import (
    RavenGunShotParser,
    SOUNDTHINKING_OUI,
    RAVEN_SERVICE_UUIDS,
    RAVEN_LEGACY_UUIDS,
)


@pytest.fixture
def parser():
    return RavenGunShotParser()


def make_raw(
    mac_address="D4:11:D6:AA:BB:CC",
    manufacturer_data=None,
    service_uuids=None,
    service_data=None,
    local_name=None,
    **kwargs,
):
    defaults = dict(
        timestamp="2026-04-10T00:00:00+00:00",
        address_type="public",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        mac_address=mac_address,
        manufacturer_data=manufacturer_data,
        service_uuids=service_uuids or [],
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


class TestRavenBasicDetection:
    """Raven detected by SoundThinking OUI prefix D4:11:D6."""

    def test_parse_by_oui(self, parser):
        raw = make_raw(mac_address="D4:11:D6:AA:BB:CC")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.parser_name == "raven_gunshot"

    def test_beacon_type(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.beacon_type == "raven_gunshot"

    def test_device_class(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result.device_class == "surveillance"

    def test_non_soundthinking_mac_returns_none(self, parser):
        raw = make_raw(mac_address="AA:BB:CC:DD:EE:FF")
        assert parser.parse(raw) is None


class TestRavenFirmwareEstimation:
    """Firmware version estimated from advertised service UUIDs."""

    def test_fw_1_1_legacy_uuids(self, parser):
        raw = make_raw(service_uuids=[
            "00001809-0000-1000-8000-00805f9b34fb",  # Health (legacy)
            "00001819-0000-1000-8000-00805f9b34fb",  # Location (legacy)
        ])
        result = parser.parse(raw)
        assert result.metadata["firmware_estimate"] == "1.1.x"

    def test_fw_1_2_gps_no_power(self, parser):
        raw = make_raw(service_uuids=[
            "00003100-0000-1000-8000-00805f9b34fb",  # GPS
            "0000180a-0000-1000-8000-00805f9b34fb",  # Device Info
        ])
        result = parser.parse(raw)
        assert result.metadata["firmware_estimate"] == "1.2.x"

    def test_fw_1_3_gps_and_power(self, parser):
        raw = make_raw(service_uuids=[
            "00003100-0000-1000-8000-00805f9b34fb",  # GPS
            "00003200-0000-1000-8000-00805f9b34fb",  # Power
            "0000180a-0000-1000-8000-00805f9b34fb",  # Device Info
        ])
        result = parser.parse(raw)
        assert result.metadata["firmware_estimate"] == "1.3.x"

    def test_fw_unknown_no_service_uuids(self, parser):
        raw = make_raw(service_uuids=[])
        result = parser.parse(raw)
        assert result.metadata["firmware_estimate"] == "unknown"


class TestRavenServiceDetection:
    """Advertised service UUIDs mapped to capabilities."""

    def test_detects_gps_service(self, parser):
        raw = make_raw(service_uuids=[
            "00003100-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "gps" in result.metadata["services"]

    def test_detects_power_service(self, parser):
        raw = make_raw(service_uuids=[
            "00003200-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "power" in result.metadata["services"]

    def test_detects_network_service(self, parser):
        raw = make_raw(service_uuids=[
            "00003300-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "network" in result.metadata["services"]

    def test_detects_uploads_service(self, parser):
        raw = make_raw(service_uuids=[
            "00003400-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "uploads" in result.metadata["services"]

    def test_detects_diagnostics_service(self, parser):
        raw = make_raw(service_uuids=[
            "00003500-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "diagnostics" in result.metadata["services"]

    def test_detects_device_info_service(self, parser):
        raw = make_raw(service_uuids=[
            "0000180a-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "device_info" in result.metadata["services"]

    def test_detects_legacy_health_service(self, parser):
        raw = make_raw(service_uuids=[
            "00001809-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "health_legacy" in result.metadata["services"]

    def test_detects_legacy_location_service(self, parser):
        raw = make_raw(service_uuids=[
            "00001819-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        assert "location_legacy" in result.metadata["services"]

    def test_no_services_when_no_uuids(self, parser):
        raw = make_raw(service_uuids=[])
        result = parser.parse(raw)
        assert result.metadata["services"] == []

    def test_multiple_services_detected(self, parser):
        raw = make_raw(service_uuids=[
            "00003100-0000-1000-8000-00805f9b34fb",
            "00003200-0000-1000-8000-00805f9b34fb",
            "00003300-0000-1000-8000-00805f9b34fb",
        ])
        result = parser.parse(raw)
        services = result.metadata["services"]
        assert "gps" in services
        assert "power" in services
        assert "network" in services


class TestRavenIdentityHash:
    def test_hash_format(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_hash_uses_mac(self, parser):
        raw1 = make_raw(mac_address="D4:11:D6:00:00:01")
        raw2 = make_raw(mac_address="D4:11:D6:00:00:02")
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash

    def test_hash_prefix(self, parser):
        """Identity uses 'raven:' prefix for namespace separation from flock."""
        mac = "D4:11:D6:AA:BB:CC"
        raw = make_raw(mac_address=mac)
        result = parser.parse(raw)
        expected = hashlib.sha256(f"raven:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestRavenMetadata:
    def test_includes_device_name_when_present(self, parser):
        raw = make_raw(local_name="Raven-12345")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Raven-12345"

    def test_no_device_name_key_when_absent(self, parser):
        raw = make_raw(local_name=None)
        result = parser.parse(raw)
        assert "device_name" not in result.metadata

    def test_manufacturer_data_captured(self, parser):
        mfr = b"\x01\x02\x03\x04"
        raw = make_raw(manufacturer_data=mfr)
        result = parser.parse(raw)
        assert result.raw_payload_hex == mfr.hex()

    def test_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        result = parser.parse(raw)
        assert result.raw_payload_hex is None


class TestRavenConstants:
    def test_soundthinking_oui(self):
        assert SOUNDTHINKING_OUI == "D4:11:D6"

    def test_raven_service_uuids_count(self):
        # 6 standard services: device_info, gps, power, network, uploads, diagnostics
        assert len(RAVEN_SERVICE_UUIDS) == 6

    def test_raven_legacy_uuids_count(self):
        # 2 legacy services: health, location
        assert len(RAVEN_LEGACY_UUIDS) == 2


class TestRavenStorageSchema:
    def test_no_storage(self, parser):
        assert parser.storage_schema() is None
