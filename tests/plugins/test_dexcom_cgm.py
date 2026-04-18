"""Tests for Dexcom CGM plugin.

Identifiers per apk-ble-hunting/reports/dexcom-g6_passive.md and
reports/dexcom-g7_passive.md. The earlier test file pinned a UUID that
wasn't actually Dexcom's; the constants are now the SIG-registered FEBC
(G6) and the community-documented G7 UUID.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.dexcom_cgm import (
    DexcomCgmParser,
    DEXCOM_G6_SERVICE_UUID,
    DEXCOM_G7_SERVICE_UUID,
)


@pytest.fixture
def parser():
    return DexcomCgmParser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-09T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


DEVICE_INFO_UUID = "180a"


class TestDexcomConstants:
    def test_g6_uuid_is_febc(self):
        assert DEXCOM_G6_SERVICE_UUID == "febc"

    def test_g7_uuid(self):
        assert DEXCOM_G7_SERVICE_UUID == "f8083532-849e-531c-c594-30f1f86a4ea5"


class TestDexcomParsing:
    def test_parse_by_g6_service_uuid(self, parser):
        raw = make_raw(service_uuids=[DEVICE_INFO_UUID, DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G6"

    def test_parse_by_g7_service_uuid(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G7_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G7"

    def test_parse_by_g6_name_format(self, parser):
        raw = make_raw(local_name="Dexcom8X")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G6"
        assert result.metadata["transmitter_serial_tail"] == "8X"

    def test_parse_by_g7_name_prefix(self, parser):
        raw = make_raw(local_name="DXCMXYZ123")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G7"

    def test_parse_result_fields(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.parser_name == "dexcom_cgm"
        assert result.beacon_type == "dexcom_cgm"
        assert result.device_class == "medical"

    def test_identity_hash_uses_serial_tail_when_available(self, parser):
        raw = make_raw(local_name="Dexcom8X", mac_address="11:22:33:44:55:66")
        result = parser.parse(raw)
        expected = hashlib.sha256("dexcom_g6:8X".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_fallback(self, parser):
        raw = make_raw(
            service_uuids=[DEXCOM_G7_SERVICE_UUID], mac_address="11:22:33:44:55:66"
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_metadata_device_name(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID], local_name="Dexcom8X")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Dexcom8X"

    def test_has_device_info_flag(self, parser):
        raw = make_raw(service_uuids=[DEVICE_INFO_UUID, DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.metadata.get("has_device_info") is True

    def test_no_device_info_flag(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.metadata.get("has_device_info") is not True


class TestDexcomNoMatch:
    def test_unrelated_uuid(self, parser):
        raw = make_raw(service_uuids=["1234"], local_name="SomeDevice")
        assert parser.parse(raw) is None

    def test_empty_ad(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_plain_dex_name_does_not_match(self, parser):
        # "DEX" alone isn't in the documented Dexcom name format.
        raw = make_raw(local_name="DEX")
        assert parser.parse(raw) is None

    def test_dexcom_prefix_but_wrong_length(self, parser):
        # "DexcomABC" is 9 chars — G6 format is exactly 8 (Dexcom + 2).
        raw = make_raw(local_name="DexcomABC")
        assert parser.parse(raw) is None
