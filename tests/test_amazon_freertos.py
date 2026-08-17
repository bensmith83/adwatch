"""Tests for the AmazonFreeRTOS BLE onboarding plugin.

Source: apk-ble-hunting/reports/pentair-pentairhome_passive.md, which cites
`com/amazon/aws/amazonfreertossdk/AmazonFreeRTOSManager.java:70` scanning on
service UUID `8a7f1168-48af-4efb-83b5-e679f932ff00` and names it the
AmazonFreeRTOS DEVICE_INFO service.

The same two custom 128-bit UUIDs (`8a7f1168-…ff00` and
`a9d7166a-…30100`) also appear in the unrelated Bird Buddy bird-feeder
bundle (`birdbuddy-app.md:79,83`), which is what establishes them as SDK
service UUIDs rather than per-vendor ones.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.amazon_freertos import (
    AmazonFreeRTOSParser,
    AFR_DEVICE_INFO_UUID,
    AFR_MQTT_PROXY_UUID,
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


def _registry():
    registry = ParserRegistry()

    @register_parser(
        name="amazon_freertos",
        service_uuid=[AFR_DEVICE_INFO_UUID, AFR_MQTT_PROXY_UUID],
        description="AmazonFreeRTOS",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(AmazonFreeRTOSParser):
        pass

    return registry


class TestAfrConstants:
    def test_device_info_uuid(self):
        assert AFR_DEVICE_INFO_UUID == "8a7f1168-48af-4efb-83b5-e679f932ff00"

    def test_mqtt_proxy_uuid(self):
        assert AFR_MQTT_PROXY_UUID == "a9d7166a-d72e-40a9-a002-48044cc30100"


class TestAfrMatching:
    def test_matches_device_info_uuid(self):
        assert len(_registry().match(_make_ad(service_uuids=[AFR_DEVICE_INFO_UUID]))) == 1

    def test_matches_mqtt_proxy_uuid(self):
        assert len(_registry().match(_make_ad(service_uuids=[AFR_MQTT_PROXY_UUID]))) == 1

    def test_matches_uppercase(self):
        ad = _make_ad(service_uuids=[AFR_DEVICE_INFO_UUID.upper()])
        assert len(_registry().match(ad)) == 1

    def test_does_not_match_other_uuid(self):
        ad = _make_ad(service_uuids=["021a9004-0382-4aea-bff4-6b3f1c5adfb4"])
        assert _registry().match(ad) == []

    def test_parse_rejects_without_uuid(self):
        assert AmazonFreeRTOSParser().parse(_make_ad(local_name="whatever")) is None


class TestAfrMetadata:
    def test_core_fields(self):
        result = AmazonFreeRTOSParser().parse(_make_ad(service_uuids=[AFR_DEVICE_INFO_UUID]))
        assert result is not None
        assert result.parser_name == "amazon_freertos"
        assert result.beacon_type == "amazon_freertos"
        assert result.device_class == "provisioning"
        assert result.metadata["sdk"] == "amazon-freertos"
        assert result.metadata["vendor_agnostic"] is True

    def test_device_info_service_flagged(self):
        result = AmazonFreeRTOSParser().parse(_make_ad(service_uuids=[AFR_DEVICE_INFO_UUID]))
        assert result.metadata["services"] == "device_info"

    def test_mqtt_proxy_service_flagged(self):
        result = AmazonFreeRTOSParser().parse(_make_ad(service_uuids=[AFR_MQTT_PROXY_UUID]))
        assert result.metadata["services"] == "mqtt_proxy"

    def test_both_services_flagged(self):
        result = AmazonFreeRTOSParser().parse(
            _make_ad(service_uuids=[AFR_MQTT_PROXY_UUID, AFR_DEVICE_INFO_UUID]))
        assert result.metadata["services"] == "device_info,mqtt_proxy"

    def test_device_name_recorded(self):
        result = AmazonFreeRTOSParser().parse(
            _make_ad(service_uuids=[AFR_DEVICE_INFO_UUID], local_name="AFR-1234"))
        assert result.metadata["device_name"] == "AFR-1234"

    def test_matches_via_service_data_key(self):
        result = AmazonFreeRTOSParser().parse(
            _make_ad(service_data={AFR_DEVICE_INFO_UUID: b"\x01"}))
        assert result is not None


class TestAfrIdentity:
    def test_identity_hash_from_mac(self):
        result = AmazonFreeRTOSParser().parse(
            _make_ad(service_uuids=[AFR_DEVICE_INFO_UUID], mac_address="11:22:33:44:55:66"))
        expected = hashlib.sha256(b"amazon_freertos:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self):
        result = AmazonFreeRTOSParser().parse(_make_ad(service_uuids=[AFR_DEVICE_INFO_UUID]))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestBirdBuddyDisambiguation:
    """birdbuddy.py registers the same two SDK UUIDs; make the overlap explicit."""

    def test_birdbuddy_yields_uuid_only_ads_to_us(self):
        from adwatch.plugins.birdbuddy import BirdBuddyParser, BIRDBUDDY_V1_UUID
        ad = _make_ad(service_uuids=[BIRDBUDDY_V1_UUID])
        assert BirdBuddyParser().parse(ad) is None
        assert AmazonFreeRTOSParser().parse(ad) is not None

    def test_we_stand_down_when_name_is_a_bird_buddy(self):
        from adwatch.plugins.birdbuddy import BirdBuddyParser, BIRDBUDDY_V1_UUID
        ad = _make_ad(service_uuids=[BIRDBUDDY_V1_UUID], local_name="BbBUDDY")
        assert AmazonFreeRTOSParser().parse(ad) is None
        assert BirdBuddyParser().parse(ad) is not None

    def test_birdbuddy_confident_when_name_matches(self):
        from adwatch.plugins.birdbuddy import BirdBuddyParser, BIRDBUDDY_V1_UUID
        result = BirdBuddyParser().parse(
            _make_ad(service_uuids=[BIRDBUDDY_V1_UUID], local_name="BbBUDDY"))
        assert "uuid_is_shared_afr_service" not in result.metadata
        assert result.metadata["confidence"] == "high"
