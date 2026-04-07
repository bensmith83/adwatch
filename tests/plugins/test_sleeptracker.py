"""Tests for SleepTracker (Beautyrest) plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.sleeptracker import SleepTrackerParser


@pytest.fixture
def parser():
    return SleepTrackerParser()


def make_raw(manufacturer_data=None, service_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


SLEEPTRACKER_MFR = bytes.fromhex("ef010022979b3c06010f")
SLEEPTRACKER_UUID = "f6380280-6d90-442c-8feb-3aec76948f06"


class TestSleepTrackerParsing:
    def test_parse_valid_data(self, parser):
        raw = make_raw(
            manufacturer_data=SLEEPTRACKER_MFR,
            service_uuids=[SLEEPTRACKER_UUID],
            local_name="SleepTracker",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert result.parser_name == "sleeptracker"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert result.beacon_type == "sleeptracker"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert result.device_class == "health"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            manufacturer_data=SLEEPTRACKER_MFR,
            local_name="SleepTracker",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("sleeptracker:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_state(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert result.metadata["device_state"] == 0x22

    def test_device_id(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "979b3c06"

    def test_firmware_info(self, parser):
        raw = make_raw(manufacturer_data=SLEEPTRACKER_MFR, local_name="SleepTracker")
        result = parser.parse(raw)
        assert result.metadata["firmware_info"] == "010f"


class TestSleepTrackerMalformed:
    def test_returns_none_no_mfr_data(self, parser):
        raw = make_raw(local_name="SleepTracker")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c000022979b3c06010f"))
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("ef01"))
        assert parser.parse(raw) is None


class TestSleepTrackerPluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "SleepTracker"
