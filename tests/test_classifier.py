"""Tests for adwatch.classifier — broad advertisement classification."""

import re

import pytest
from adwatch.models import RawAdvertisement, Classification
from adwatch.classifier import (
    COMPANY_ID_REGISTRY,
    SERVICE_UUID_REGISTRY,
    LOCAL_NAME_PATTERNS,
    APPLE_SUBTYPE_REGISTRY,
    Classifier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ad(
    *,
    manufacturer_data: bytes | None = None,
    service_uuids: list[str] | None = None,
    service_data: dict[str, bytes] | None = None,
    local_name: str | None = None,
) -> RawAdvertisement:
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        rssi=-60,
        tx_power=None,
    )


@pytest.fixture
def classifier():
    return Classifier()


# ===================================================================
# COMPANY_ID_REGISTRY data tests
# ===================================================================

class TestCompanyIdRegistry:
    """Verify COMPANY_ID_REGISTRY contains expected entries."""

    def test_apple_entry(self):
        assert 0x004C in COMPANY_ID_REGISTRY
        ad_type, ad_category = COMPANY_ID_REGISTRY[0x004C]
        assert ad_type == "apple"
        assert ad_category == "phone"

    def test_samsung_entry(self):
        assert 0x0075 in COMPANY_ID_REGISTRY
        ad_type, ad_category = COMPANY_ID_REGISTRY[0x0075]
        assert ad_type == "samsung"
        assert ad_category == "phone"

    def test_microsoft_entry(self):
        assert 0x0006 in COMPANY_ID_REGISTRY
        ad_type, ad_category = COMPANY_ID_REGISTRY[0x0006]
        assert ad_type == "microsoft"
        assert ad_category == "computer"

    def test_google_entry(self):
        assert 0x00E0 in COMPANY_ID_REGISTRY
        ad_type, ad_category = COMPANY_ID_REGISTRY[0x00E0]
        assert ad_type == "google"
        assert ad_category == "phone"

    def test_xiaomi_entry(self):
        assert 0x038F in COMPANY_ID_REGISTRY
        ad_type, ad_category = COMPANY_ID_REGISTRY[0x038F]
        assert ad_type == "xiaomi"
        assert ad_category == "phone"

    def test_sonos_entry(self):
        assert 0x05A7 in COMPANY_ID_REGISTRY
        ad_type, ad_category = COMPANY_ID_REGISTRY[0x05A7]
        assert ad_type == "sonos"
        assert ad_category == "speaker"

    def test_registry_values_are_tuples(self):
        """Every registry value must be a (str, str) tuple."""
        for company_id, value in COMPANY_ID_REGISTRY.items():
            assert isinstance(value, tuple), f"0x{company_id:04X}: expected tuple"
            assert len(value) == 2, f"0x{company_id:04X}: expected 2-tuple"
            assert isinstance(value[0], str), f"0x{company_id:04X}: ad_type not str"
            assert isinstance(value[1], str), f"0x{company_id:04X}: ad_category not str"


# ===================================================================
# SERVICE_UUID_REGISTRY data tests
# ===================================================================

class TestServiceUuidRegistry:
    """Verify SERVICE_UUID_REGISTRY contains expected entries."""

    def test_fast_pair_entry(self):
        # Should match the full 128-bit UUID form or the short 16-bit form
        found = False
        for key in SERVICE_UUID_REGISTRY:
            if "fe2c" in key.lower():
                found = True
                ad_type, ad_category = SERVICE_UUID_REGISTRY[key]
                assert ad_type == "fast_pair"
                assert ad_category == "accessory"
                break
        assert found, "Fast Pair UUID (fe2c) not found in SERVICE_UUID_REGISTRY"

    def test_matter_entry(self):
        found = False
        for key in SERVICE_UUID_REGISTRY:
            if "fff6" in key.lower():
                found = True
                ad_type, ad_category = SERVICE_UUID_REGISTRY[key]
                assert ad_type == "matter"
                assert ad_category == "smart_home"
                break
        assert found, "Matter UUID (fff6) not found in SERVICE_UUID_REGISTRY"

    def test_tile_entry(self):
        found = False
        for key in SERVICE_UUID_REGISTRY:
            if "feed" in key.lower():
                found = True
                ad_type, ad_category = SERVICE_UUID_REGISTRY[key]
                assert ad_type == "tile"
                assert ad_category == "tracker"
                break
        assert found, "Tile UUID (feed) not found in SERVICE_UUID_REGISTRY"

    def test_smarttag_entry(self):
        found = False
        for key in SERVICE_UUID_REGISTRY:
            if "fd5a" in key.lower():
                found = True
                ad_type, ad_category = SERVICE_UUID_REGISTRY[key]
                assert ad_type == "smarttag"
                assert ad_category == "tracker"
                break
        assert found, "SmartTag UUID (fd5a) not found in SERVICE_UUID_REGISTRY"

    def test_registry_values_are_tuples(self):
        for uuid_key, value in SERVICE_UUID_REGISTRY.items():
            assert isinstance(value, tuple), f"{uuid_key}: expected tuple"
            assert len(value) == 2, f"{uuid_key}: expected 2-tuple"


# ===================================================================
# APPLE_SUBTYPE_REGISTRY data tests
# ===================================================================

class TestAppleSubtypeRegistry:

    def test_nearby_info(self):
        assert 0x10 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x10]
        assert ad_type == "apple_nearby"
        assert ad_category == "phone"

    def test_handoff(self):
        assert 0x0C in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x0C]
        assert ad_type == "apple_handoff"
        assert ad_category == "phone"

    def test_findmy(self):
        assert 0x12 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x12]
        assert ad_type == "apple_findmy"
        assert ad_category == "tracker"

    def test_airpods(self):
        assert 0x07 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x07]
        assert ad_type == "apple_proximity"
        assert ad_category == "accessory"

    def test_airdrop(self):
        assert 0x05 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x05]
        assert ad_type == "apple_airdrop"
        assert ad_category == "phone"

    def test_airplay(self):
        assert 0x09 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x09]
        assert ad_type == "apple_airplay"
        assert ad_category == "media"

    def test_nearby_action(self):
        assert 0x0F in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x0F]
        assert ad_type == "apple_nearby_action"
        assert ad_category == "phone"

    def test_ibeacon(self):
        assert 0x02 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x02]
        assert ad_type == "ibeacon"
        assert ad_category == "beacon"

    def test_homekit(self):
        assert 0x06 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x06]
        assert ad_type == "apple_homekit"
        assert ad_category == "iot"

    def test_siri(self):
        assert 0x08 in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x08]
        assert ad_type == "apple_siri"
        assert ad_category == "phone"

    def test_magic_switch(self):
        assert 0x0B in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x0B]
        assert ad_type == "apple_magic_switch"
        assert ad_category == "phone"

    def test_tethering(self):
        assert 0x0D in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x0D]
        assert ad_type == "apple_tethering"
        assert ad_category == "phone"

    def test_tethering_source(self):
        assert 0x0E in APPLE_SUBTYPE_REGISTRY
        ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[0x0E]
        assert ad_type == "apple_tethering_source"
        assert ad_category == "phone"

    def test_registry_values_are_tuples(self):
        for subtype, value in APPLE_SUBTYPE_REGISTRY.items():
            assert isinstance(value, tuple), f"0x{subtype:02X}: expected tuple"
            assert len(value) == 2, f"0x{subtype:02X}: expected 2-tuple"


# ===================================================================
# LOCAL_NAME_PATTERNS data tests
# ===================================================================

class TestLocalNamePatterns:

    def test_patterns_is_list_of_tuples(self):
        assert isinstance(LOCAL_NAME_PATTERNS, list)
        for entry in LOCAL_NAME_PATTERNS:
            assert isinstance(entry, tuple), f"Expected tuple, got {type(entry)}"
            assert len(entry) == 3, f"Expected 3-tuple (regex, ad_type, ad_category)"
            pattern, ad_type, ad_category = entry
            assert isinstance(pattern, (str, re.Pattern))
            assert isinstance(ad_type, str)
            assert isinstance(ad_category, str)

    def test_thermopro_pattern_matches(self):
        """A ThermoPro local name like 'TP357 (2B54)' should match."""
        matched = False
        for pattern, ad_type, ad_category in LOCAL_NAME_PATTERNS:
            if re.search(pattern, "TP357 (2B54)"):
                matched = True
                assert ad_type == "thermopro"
                assert ad_category == "sensor"
                break
        assert matched, "No pattern matched 'TP357 (2B54)'"

    def test_iphone_pattern_matches(self):
        matched = False
        for pattern, ad_type, ad_category in LOCAL_NAME_PATTERNS:
            if re.search(pattern, "iPhone"):
                matched = True
                assert ad_type == "apple"
                assert ad_category == "phone"
                break
        assert matched, "No pattern matched 'iPhone'"

    def test_sonos_pattern_matches(self):
        matched = False
        for pattern, ad_type, ad_category in LOCAL_NAME_PATTERNS:
            if re.search(pattern, "Sonos One"):
                matched = True
                assert ad_type == "sonos"
                assert ad_category == "speaker"
                break
        assert matched, "No pattern matched 'Sonos One'"

    def test_flipper_pattern_matches(self):
        matched = False
        for pattern, ad_type, ad_category in LOCAL_NAME_PATTERNS:
            if re.search(pattern, "Flipper Zero"):
                matched = True
                assert ad_type == "flipper"
                assert ad_category == "tool"
                break
        assert matched, "No pattern matched 'Flipper Zero'"


# ===================================================================
# Classifier.classify() — Apple company_id with subtypes
# ===================================================================

class TestClassifyAppleSubtypes:
    """Apple ads (company_id 0x004C) should be classified by TLV subtype."""

    def test_nearby_info(self, classifier, apple_nearby_ad):
        result = classifier.classify(apple_nearby_ad)
        assert result is not None
        assert result.ad_type == "apple_nearby"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_handoff(self, classifier):
        # 0x4C 0x00 = company_id, 0x0C = Handoff type, 0x03 = length
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x0c\x03\x01\x02\x03")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_handoff"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_findmy(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x12\x19" + b"\x00" * 25)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_findmy"
        assert result.ad_category == "tracker"
        assert result.source == "company_id"

    def test_airpods_proximity(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x07\x19" + b"\x00" * 25)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_proximity"
        assert result.ad_category == "accessory"
        assert result.source == "company_id"

    def test_airdrop(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x05\x12" + b"\x00" * 18)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_airdrop"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_airplay(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x09\x06" + b"\x00" * 6)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_airplay"
        assert result.ad_category == "media"
        assert result.source == "company_id"

    def test_nearby_action(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x0f\x05" + b"\x00" * 5)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_nearby_action"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_ibeacon(self, classifier, ibeacon_ad):
        result = classifier.classify(ibeacon_ad)
        assert result is not None
        assert result.ad_type == "ibeacon"
        assert result.ad_category == "beacon"
        assert result.source == "company_id"

    def test_homekit(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x06\x04\x01\x02\x03\x04")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_homekit"
        assert result.ad_category == "iot"
        assert result.source == "company_id"

    def test_siri(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x08\x04\x01\x02\x03\x04")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_siri"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_magic_switch(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x0b\x04\x01\x02\x03\x04")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_magic_switch"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_tethering(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x0d\x04\x01\x02\x03\x04")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_tethering"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_tethering_source(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x0e\x04\x01\x02\x03\x04")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_tethering_source"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_apple_unknown_subtype_falls_back_to_generic(self, classifier):
        """Apple ad with unrecognized subtype should still classify as generic Apple."""
        ad = _make_ad(manufacturer_data=b"\x4c\x00\xFE\x03\x01\x02\x03")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_apple_short_payload_no_subtype(self, classifier):
        """Apple ad with only company_id (no payload) should classify as generic Apple."""
        ad = _make_ad(manufacturer_data=b"\x4c\x00")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple"
        assert result.ad_category == "phone"
        assert result.source == "company_id"


# ===================================================================
# Classifier.classify() — non-Apple company IDs
# ===================================================================

class TestClassifyCompanyIds:

    def test_samsung(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x75\x00\x01\x02\x03")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "samsung"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_microsoft(self, classifier, microsoft_cdp_ad):
        result = classifier.classify(microsoft_cdp_ad)
        assert result is not None
        assert result.ad_type == "microsoft"
        assert result.ad_category == "computer"
        assert result.source == "company_id"

    def test_google(self, classifier):
        ad = _make_ad(manufacturer_data=b"\xe0\x00\x01\x02\x03")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "google"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_xiaomi(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x8f\x03\x01\x02\x03")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "xiaomi"
        assert result.ad_category == "phone"
        assert result.source == "company_id"

    def test_sonos(self, classifier):
        ad = _make_ad(manufacturer_data=b"\xa7\x05\x01\x02\x03")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "sonos"
        assert result.ad_category == "speaker"
        assert result.source == "company_id"


# ===================================================================
# Classifier.classify() — service UUID matches
# ===================================================================

class TestClassifyServiceUuids:

    def test_fast_pair(self, classifier, fast_pair_ad):
        result = classifier.classify(fast_pair_ad)
        assert result is not None
        assert result.ad_type == "fast_pair"
        assert result.ad_category == "accessory"
        assert result.source == "service_uuid"

    def test_matter(self, classifier):
        ad = _make_ad(
            service_uuids=["0000fff6-0000-1000-8000-00805f9b34fb"],
            service_data={"0000fff6-0000-1000-8000-00805f9b34fb": b"\x00"},
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "matter"
        assert result.ad_category == "smart_home"
        assert result.source == "service_uuid"

    def test_tile(self, classifier):
        ad = _make_ad(
            service_uuids=["0000feed-0000-1000-8000-00805f9b34fb"],
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "tile"
        assert result.ad_category == "tracker"
        assert result.source == "service_uuid"

    def test_smarttag(self, classifier):
        ad = _make_ad(
            service_uuids=["0000fd5a-0000-1000-8000-00805f9b34fb"],
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "smarttag"
        assert result.ad_category == "tracker"
        assert result.source == "service_uuid"


# ===================================================================
# Classifier.classify() — local name pattern matches
# ===================================================================

class TestClassifyLocalName:

    def test_thermopro(self, classifier, thermopro_ad):
        result = classifier.classify(thermopro_ad)
        assert result is not None
        assert result.ad_type == "thermopro"
        assert result.ad_category == "sensor"
        assert result.source == "local_name"

    def test_thermopro_variant(self, classifier):
        ad = _make_ad(local_name="TP393S (A1B2)")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "thermopro"
        assert result.ad_category == "sensor"
        assert result.source == "local_name"

    def test_iphone(self, classifier):
        ad = _make_ad(local_name="iPhone")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple"
        assert result.ad_category == "phone"
        assert result.source == "local_name"

    def test_sonos_name(self, classifier):
        ad = _make_ad(local_name="Sonos One")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "sonos"
        assert result.ad_category == "speaker"
        assert result.source == "local_name"

    def test_flipper(self, classifier):
        ad = _make_ad(local_name="Flipper Zero")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "flipper"
        assert result.ad_category == "tool"
        assert result.source == "local_name"


# ===================================================================
# Classifier.classify() — unknown / None
# ===================================================================

class TestClassifyUnknown:

    def test_unknown_company_id(self, classifier, unknown_ad):
        """Company ID 0xFFFF is not registered -- should return None."""
        result = classifier.classify(unknown_ad)
        assert result is None

    def test_no_data_at_all(self, classifier):
        ad = _make_ad()
        result = classifier.classify(ad)
        assert result is None

    def test_empty_manufacturer_data(self, classifier):
        ad = _make_ad(manufacturer_data=b"")
        result = classifier.classify(ad)
        assert result is None

    def test_unrecognized_service_uuid(self, classifier):
        ad = _make_ad(service_uuids=["00001234-0000-1000-8000-00805f9b34fb"])
        result = classifier.classify(ad)
        assert result is None

    def test_unrecognized_local_name(self, classifier):
        ad = _make_ad(local_name="SomeRandomBleDevice42")
        result = classifier.classify(ad)
        assert result is None


# ===================================================================
# Priority: company_id > service_uuid > local_name
# ===================================================================

class TestClassifyPriority:
    """When multiple match sources are present, priority order must hold."""

    def test_company_id_beats_service_uuid(self, classifier):
        """company_id should take priority over service_uuid."""
        ad = _make_ad(
            manufacturer_data=b"\x75\x00\x01\x02\x03",  # Samsung
            service_uuids=["0000feed-0000-1000-8000-00805f9b34fb"],  # Tile
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.source == "company_id"
        assert result.ad_type == "samsung"

    def test_company_id_beats_local_name(self, classifier):
        """company_id should take priority over local_name."""
        ad = _make_ad(
            manufacturer_data=b"\x75\x00\x01\x02\x03",  # Samsung
            local_name="Flipper Zero",  # Flipper
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.source == "company_id"
        assert result.ad_type == "samsung"

    def test_service_uuid_beats_local_name(self, classifier):
        """service_uuid should take priority over local_name."""
        ad = _make_ad(
            service_uuids=["0000feed-0000-1000-8000-00805f9b34fb"],  # Tile
            local_name="Flipper Zero",  # Flipper
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.source == "service_uuid"
        assert result.ad_type == "tile"

    def test_falls_through_to_local_name(self, classifier):
        """Unknown company_id + unknown UUID should fall through to local_name."""
        ad = _make_ad(
            manufacturer_data=b"\xFF\xFF\x01\x02",  # unknown
            service_uuids=["00001234-0000-1000-8000-00805f9b34fb"],  # unknown
            local_name="TP357 (2B54)",  # ThermoPro
        )
        result = classifier.classify(ad)
        assert result is not None
        assert result.source == "local_name"
        assert result.ad_type == "thermopro"


# ===================================================================
# Apple subtype overrides generic Apple
# ===================================================================

class TestAppleSubtypeOverridesGeneric:
    """When an Apple ad has a recognized subtype, the subtype classification
    should be used instead of the generic 'apple' classification."""

    def test_nearby_overrides_generic(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x10\x05\x01\x18\x44\x00\x00")
        result = classifier.classify(ad)
        assert result is not None
        # Must be specific subtype, NOT generic "apple"
        assert result.ad_type == "apple_nearby"
        assert result.ad_type != "apple"

    def test_findmy_overrides_generic(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x12\x19" + b"\x00" * 25)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_findmy"
        assert result.ad_category == "tracker"
        # Category should NOT be generic "phone"
        assert result.ad_category != "phone"

    def test_ibeacon_overrides_generic(self, classifier):
        uuid_bytes = bytes.fromhex("B9407F30F5F8466EAFF925556B57FE6D")
        payload = b"\x4c\x00\x02\x15" + uuid_bytes + b"\x00\x01\x00\x02\xC5"
        ad = _make_ad(manufacturer_data=payload)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "ibeacon"
        assert result.ad_category == "beacon"

    def test_airpods_overrides_generic(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x07\x19" + b"\x00" * 25)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "apple_proximity"
        assert result.ad_category == "accessory"


# ===================================================================
# Classification return type
# ===================================================================

class TestClassificationReturnType:

    def test_returns_classification_instance(self, classifier, apple_nearby_ad):
        result = classifier.classify(apple_nearby_ad)
        assert isinstance(result, Classification)

    def test_returns_none_for_unknown(self, classifier, unknown_ad):
        result = classifier.classify(unknown_ad)
        assert result is None

    def test_source_field_valid_values(self, classifier, apple_nearby_ad, fast_pair_ad, thermopro_ad):
        r1 = classifier.classify(apple_nearby_ad)
        assert r1.source in ("company_id", "service_uuid", "local_name")

        r2 = classifier.classify(fast_pair_ad)
        assert r2.source in ("company_id", "service_uuid", "local_name")

        r3 = classifier.classify(thermopro_ad)
        assert r3.source in ("company_id", "service_uuid", "local_name")


class TestGoveeClassification:
    """Govee sensors should be classified by company_id and local_name."""

    def test_govee_thermometer_by_company_id(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x88\xEC" + b"\x00" * 7)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "govee"
        assert result.ad_category == "sensor"
        assert result.source == "company_id"

    def test_govee_vibration_by_company_id(self, classifier):
        ad = _make_ad(manufacturer_data=b"\x88\xEF" + b"\x00" * 24)
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "govee"
        assert result.ad_category == "sensor"
        assert result.source == "company_id"

    def test_govee_vibration_by_local_name(self, classifier):
        ad = _make_ad(local_name="GV51242F04")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "govee"
        assert result.source == "local_name"

    def test_govee_thermometer_by_local_name(self, classifier):
        ad = _make_ad(local_name="GVH5074_1234")
        result = classifier.classify(ad)
        assert result is not None
        assert result.ad_type == "govee"
        assert result.source == "local_name"
