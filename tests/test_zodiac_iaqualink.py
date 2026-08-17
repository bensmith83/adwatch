"""Tests for the Zodiac iAquaLink pool-equipment plugin.

Source: apk-ble-hunting/reports/zodiac-iaqualink_passive.md.
`BleConnectViewModel.java:136-146` sets an OS-level ScanFilter on the
advertised vendor service UUID `3D3A3B57-91AA-4344-810C-66C7E964ABEF`
(`UUIDConstants.java:24`) and post-filters on the family name prefixes
`iAqua_` / `vortrax` / `robotic_cleaner` (`UUIDConstants.java:18-20`).
No manufacturer data and no service data are parsed.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.zodiac_iaqualink import (
    ZodiacIAquaLinkParser,
    ZODIAC_ADV_SERVICE_UUID,
    ZODIAC_NAME_PATTERN,
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
        name="zodiac_iaqualink",
        service_uuid=ZODIAC_ADV_SERVICE_UUID,
        local_name_pattern=ZODIAC_NAME_PATTERN,
        description="Zodiac iAquaLink",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ZodiacIAquaLinkParser):
        pass

    return registry


class TestZodiacConstants:
    def test_advertised_service_uuid(self):
        assert ZODIAC_ADV_SERVICE_UUID == "3d3a3b57-91aa-4344-810c-66c7e964abef"


class TestZodiacMatching:
    def test_matches_advertised_uuid(self):
        ad = _make_ad(service_uuids=[ZODIAC_ADV_SERVICE_UUID])
        assert len(_registry().match(ad)) == 1

    def test_matches_uppercase_uuid(self):
        ad = _make_ad(service_uuids=[ZODIAC_ADV_SERVICE_UUID.upper()])
        assert len(_registry().match(ad)) == 1

    @pytest.mark.parametrize("name", ["iAqua_12345", "vortrax99", "robotic_cleaner_7"])
    def test_matches_family_names(self, name):
        assert len(_registry().match(_make_ad(local_name=name))) == 1

    @pytest.mark.parametrize("name", ["Dolphin", "IoT_PWS", "Aiper Seagull", "iAquaX"])
    def test_does_not_match_other_pool_devices(self, name):
        """Must not poach Maytronics / Aiper cleaners."""
        assert _registry().match(_make_ad(local_name=name)) == []

    def test_does_not_match_gatt_only_issc_uuid(self):
        """49535343-... is the post-connect Microchip service, never advertised."""
        ad = _make_ad(service_uuids=["49535343-fe7d-4ae5-8fa9-9fafd205e455"])
        assert _registry().match(ad) == []

    def test_parse_rejects_unrelated(self):
        assert ZodiacIAquaLinkParser().parse(_make_ad(local_name="Dolphin")) is None


class TestZodiacFamilies:
    def test_tcx_controller(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="iAqua_A1B2C3"))
        assert result is not None
        assert result.metadata["family"] == "tcx_controller"
        assert result.device_class == "pool_controller"
        assert result.metadata["unit_suffix"] == "A1B2C3"

    def test_vortrax(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="vortrax0042"))
        assert result.metadata["family"] == "vortrax"
        assert result.device_class == "pool_cleaner"
        assert result.metadata["unit_suffix"] == "0042"

    def test_robotic_cleaner(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="robotic_cleaner_7"))
        assert result.metadata["family"] == "vrf_robotic_cleaner"
        assert result.device_class == "pool_cleaner"

    def test_uuid_only_defaults_to_controller(self):
        result = ZodiacIAquaLinkParser().parse(
            _make_ad(service_uuids=[ZODIAC_ADV_SERVICE_UUID]))
        assert result is not None
        assert result.device_class == "pool_controller"
        assert "family" not in result.metadata
        assert result.metadata["adv_service_seen"] is True

    def test_no_suffix_when_prefix_only(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="iAqua_"))
        assert result is not None
        assert "unit_suffix" not in result.metadata


class TestZodiacMetadata:
    def test_core_fields(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="iAqua_A1B2C3"))
        assert result.parser_name == "zodiac_iaqualink"
        assert result.beacon_type == "zodiac_iaqualink"
        assert result.metadata["vendor"] == "Zodiac"
        assert result.metadata["device_name"] == "iAqua_A1B2C3"
        assert result.metadata["passive_telemetry"] is False

    def test_adv_service_flag_absent_when_name_only(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="iAqua_A1B2C3"))
        assert "adv_service_seen" not in result.metadata


class TestZodiacIdentity:
    def test_identity_from_name_suffix(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="iAqua_A1B2C3"))
        expected = hashlib.sha256(b"zodiac_iaqualink:A1B2C3").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_mac(self):
        a = ZodiacIAquaLinkParser().parse(
            _make_ad(local_name="iAqua_A1B2C3", mac_address="AA:BB:CC:DD:EE:FF"))
        b = ZodiacIAquaLinkParser().parse(
            _make_ad(local_name="iAqua_A1B2C3", mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash == b.identifier_hash

    def test_identity_falls_back_to_mac(self):
        result = ZodiacIAquaLinkParser().parse(
            _make_ad(service_uuids=[ZODIAC_ADV_SERVICE_UUID],
                     mac_address="11:22:33:44:55:66"))
        expected = hashlib.sha256(
            b"zodiac_iaqualink:mac:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self):
        result = ZodiacIAquaLinkParser().parse(_make_ad(local_name="vortrax0042"))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)
