"""Tests for the Ultrahuman Ring AIR / Pro / charger plugin.

Per apk-ble-hunting/reports/ultrahuman-android_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ultrahuman import (
    UltrahumanParser,
    ULTRAHUMAN_NAME_PATTERN,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "DA:55:66:77:88:99",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="ultrahuman",
        local_name_pattern=ULTRAHUMAN_NAME_PATTERN,
        description="Ultrahuman",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(UltrahumanParser):
        pass

    return _P


class TestUltrahumanMatching:
    def test_matches_ring_air(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="uh_A1B2C3"))) == 1

    def test_matches_ring_pro(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="up_A1B2C3"))) == 1

    def test_matches_charger(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="uc_A1B2C3"))) == 1

    def test_matches_uppercase_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="UH_A1B2C3"))) == 1

    def test_prefix_without_suffix_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="uh_")) == []

    def test_mid_name_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="my uh_A1B2C3")) == []

    def test_other_prefix_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="ux_A1B2C3")) == []

    def test_home_prefix_not_registered(self):
        """HOME_ is a common English word — too weak to claim on its own."""
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="HOME_A1B2C3")) == []

    def test_abbott_cgm_uuid_not_registered(self):
        """0xFDE3 (Ultrahuman M1 = rebadged Abbott) belongs to tandem_pump."""
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(service_uuids=["fde3"])) == []


class TestUltrahumanDecode:
    def test_ring_air_product(self):
        result = UltrahumanParser().parse(_make_ad(local_name="uh_A1B2C3"))
        assert result is not None
        assert result.metadata["product"] == "Ring AIR"
        assert result.metadata["name_prefix"] == "uh_"
        assert result.metadata["device_id"] == "A1B2C3"
        assert result.device_class == "wearable"

    def test_ring_pro_product(self):
        result = UltrahumanParser().parse(_make_ad(local_name="up_9F8E7D"))
        assert result.metadata["product"] == "Ring Pro"
        assert result.metadata["device_id"] == "9F8E7D"
        assert result.device_class == "wearable"

    def test_charger_product(self):
        result = UltrahumanParser().parse(_make_ad(local_name="uc_112233"))
        assert result.metadata["product"] == "ProCharger"
        assert result.device_class == "accessory"

    def test_uppercase_prefix_normalized(self):
        result = UltrahumanParser().parse(_make_ad(local_name="UP_ABCDEF"))
        assert result.metadata["product"] == "Ring Pro"
        assert result.metadata["name_prefix"] == "up_"

    def test_device_name_preserved_verbatim(self):
        result = UltrahumanParser().parse(_make_ad(local_name="UH_A1B2C3"))
        assert result.metadata["device_name"] == "UH_A1B2C3"

    def test_rejects_empty_suffix(self):
        assert UltrahumanParser().parse(_make_ad(local_name="uh_")) is None

    def test_rejects_missing_name(self):
        assert UltrahumanParser().parse(_make_ad()) is None

    def test_rejects_unrelated_name(self):
        assert UltrahumanParser().parse(_make_ad(local_name="Oura")) is None

    def test_no_passive_telemetry_claimed(self):
        ad = _make_ad(local_name="uh_A1B2C3", manufacturer_data=bytes([0x01, 0x02, 0x03]))
        result = UltrahumanParser().parse(ad)
        assert "battery_percent" not in result.metadata
        assert "heart_rate" not in result.metadata


class TestUltrahumanIdentityAndBasics:
    def test_identity_from_name_suffix(self):
        result = UltrahumanParser().parse(_make_ad(local_name="uh_A1B2C3"))
        expected = hashlib.sha256(b"ultrahuman:uh_a1b2c3").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_case_insensitive(self):
        a = _make_ad(local_name="uh_A1B2C3")
        b = _make_ad(local_name="UH_a1b2c3", mac_address="11:22:33:44:55:66")
        assert UltrahumanParser().parse(a).identifier_hash == \
            UltrahumanParser().parse(b).identifier_hash

    def test_identity_survives_mac_rotation(self):
        a = _make_ad(local_name="uh_A1B2C3", mac_address="AA:BB:CC:DD:EE:FF")
        b = _make_ad(local_name="uh_A1B2C3", mac_address="11:22:33:44:55:66")
        assert UltrahumanParser().parse(a).identifier_hash == \
            UltrahumanParser().parse(b).identifier_hash

    def test_different_rings_differ(self):
        a = _make_ad(local_name="uh_A1B2C3")
        b = _make_ad(local_name="uh_D4E5F6")
        assert UltrahumanParser().parse(a).identifier_hash != \
            UltrahumanParser().parse(b).identifier_hash

    def test_basics(self):
        result = UltrahumanParser().parse(_make_ad(local_name="uh_A1B2C3"))
        assert result.parser_name == "ultrahuman"
        assert result.beacon_type == "ultrahuman"
        assert result.metadata["vendor"] == "Ultrahuman"
