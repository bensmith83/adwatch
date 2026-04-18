"""Tests for Withings health-device plugin.

Identifiers per apk-ble-hunting/reports/withings-wiscale2_passive.md.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.withings import (
    WithingsParser,
    UUID_TO_MODEL,
    UNPROVISIONED_MAC,
    PROVISIONING_MAC,
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


def _mfr_with_mac(mac: str, company_id: int = 0x03F5) -> bytes:
    mac_bytes = bytes(int(x, 16) for x in mac.split(":"))
    return struct.pack("<H", company_id) + mac_bytes


@pytest.fixture
def parser():
    return WithingsParser()


class TestWithingsUUIDMatching:
    def test_wbs06_cardio_scale(self, parser):
        ad = _make_ad(service_uuids=["9990"])
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model"].startswith("WBS06")

    def test_wbs04_scale(self, parser):
        ad = _make_ad(service_uuids=["9993"])
        result = parser.parse(ad)
        assert "WBS04" in result.metadata["model"]

    def test_wpm_bpm(self, parser):
        ad = _make_ad(service_uuids=["9999"])
        result = parser.parse(ad)
        assert "WPM" in result.metadata["model"]

    def test_with_marker_custom_uuid(self, parser):
        # Any UUID with 5749-5448 in bytes 4-7 is a Withings device.
        ad = _make_ad(service_uuids=["10000050-5749-5448-0037-000000000000"])
        result = parser.parse(ad)
        assert result is not None
        assert "with_marker_uuid" in result.metadata


class TestWithingsNameMatching:
    def test_steel_hr_bl_hwa_name(self, parser):
        ad = _make_ad(local_name="bl_hwa02")
        result = parser.parse(ad)
        assert result is not None

    def test_sleep_monitor_name(self, parser):
        ad = _make_ad(local_name="WSM02")
        result = parser.parse(ad)
        assert result is not None

    def test_scale_name(self, parser):
        ad = _make_ad(local_name="WBS06")
        result = parser.parse(ad)
        assert result is not None

    def test_bpm_name(self, parser):
        ad = _make_ad(local_name="WPM04")
        result = parser.parse(ad)
        assert result is not None


class TestWithingsProvisioningState:
    def test_unprovisioned_from_mfr_mac(self, parser):
        ad = _make_ad(
            service_uuids=["9990"],
            manufacturer_data=_mfr_with_mac(UNPROVISIONED_MAC),
        )
        result = parser.parse(ad)
        assert result.metadata["provisioning_state"] == "unprovisioned"
        assert result.metadata["mfr_data_mac"] == UNPROVISIONED_MAC

    def test_provisioning_from_mfr_mac(self, parser):
        ad = _make_ad(
            service_uuids=["9990"],
            manufacturer_data=_mfr_with_mac(PROVISIONING_MAC),
        )
        result = parser.parse(ad)
        assert result.metadata["provisioning_state"] == "provisioning"

    def test_paired_from_mfr_mac(self, parser):
        ad = _make_ad(
            service_uuids=["9990"],
            manufacturer_data=_mfr_with_mac("12:34:56:78:9A:BC"),
        )
        result = parser.parse(ad)
        assert result.metadata["provisioning_state"] == "paired"


class TestWithingsIdentityHash:
    def test_paired_uses_mfr_mac(self, parser):
        device_mac = "12:34:56:78:9A:BC"
        ad = _make_ad(
            service_uuids=["9990"],
            manufacturer_data=_mfr_with_mac(device_mac),
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"withings:{device_mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_unprovisioned_uses_ble_mac(self, parser):
        ad = _make_ad(
            service_uuids=["9990"],
            manufacturer_data=_mfr_with_mac(UNPROVISIONED_MAC),
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(ad)
        expected = hashlib.sha256("withings:AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestWithingsFields:
    def test_parser_name(self, parser):
        result = parser.parse(_make_ad(service_uuids=["9990"]))
        assert result.parser_name == "withings"

    def test_device_class_medical(self, parser):
        result = parser.parse(_make_ad(service_uuids=["9990"]))
        assert result.device_class == "medical"

    def test_no_match_empty(self, parser):
        assert parser.parse(_make_ad()) is None

    def test_no_match_unrelated_uuid(self, parser):
        assert parser.parse(_make_ad(service_uuids=["1234"])) is None
