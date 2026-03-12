"""Tests for BLE MAC address type classification."""

import pytest

from adwatch.models import RawAdvertisement, classify_mac_type
from adwatch.dashboard.websocket import _serialize


class TestClassifyMacType:
    """Test the four BLE address types based on address_type + MAC MSBs."""

    def test_public_address(self):
        assert classify_mac_type("public", "00:11:22:33:44:55") == "public"

    def test_public_address_any_mac(self):
        # Public addresses don't depend on MAC bits
        assert classify_mac_type("public", "FF:11:22:33:44:55") == "public"
        assert classify_mac_type("public", "C0:11:22:33:44:55") == "public"

    def test_random_static_address(self):
        # Top 2 bits = 11 → 0xC0..0xFF first byte
        assert classify_mac_type("random", "C0:11:22:33:44:55") == "random_static"
        assert classify_mac_type("random", "FF:11:22:33:44:55") == "random_static"
        assert classify_mac_type("random", "D5:AA:BB:CC:DD:EE") == "random_static"
        assert classify_mac_type("random", "E0:00:00:00:00:00") == "random_static"

    def test_resolvable_private_address(self):
        # Top 2 bits = 01 → 0x40..0x7F first byte
        assert classify_mac_type("random", "40:11:22:33:44:55") == "resolvable_private"
        assert classify_mac_type("random", "7F:11:22:33:44:55") == "resolvable_private"
        assert classify_mac_type("random", "5A:BB:CC:DD:EE:FF") == "resolvable_private"

    def test_non_resolvable_private_address(self):
        # Top 2 bits = 00 → 0x00..0x3F first byte
        assert classify_mac_type("random", "00:11:22:33:44:55") == "non_resolvable_private"
        assert classify_mac_type("random", "3F:11:22:33:44:55") == "non_resolvable_private"
        assert classify_mac_type("random", "1A:BB:CC:DD:EE:FF") == "non_resolvable_private"

    def test_reserved_bits_10(self):
        # Top 2 bits = 10 → 0x80..0xBF - reserved in spec, classify as random_static
        # (in practice these shouldn't appear, but handle gracefully)
        assert classify_mac_type("random", "80:11:22:33:44:55") == "reserved"
        assert classify_mac_type("random", "BF:11:22:33:44:55") == "reserved"

    def test_case_insensitive_mac(self):
        assert classify_mac_type("random", "c0:11:22:33:44:55") == "random_static"
        assert classify_mac_type("random", "4a:bb:cc:dd:ee:ff") == "resolvable_private"

    def test_case_insensitive_address_type(self):
        assert classify_mac_type("Public", "00:11:22:33:44:55") == "public"
        assert classify_mac_type("RANDOM", "C0:11:22:33:44:55") == "random_static"


class TestRawAdvertisementMacType:
    """Test the mac_type property on RawAdvertisement."""

    def test_public_ad(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="00:11:22:33:44:55",
            address_type="public",
            manufacturer_data=None,
            service_data=None,
        )
        assert raw.mac_type == "public"

    def test_random_static_ad(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="C0:11:22:33:44:55",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        assert raw.mac_type == "random_static"

    def test_resolvable_private_ad(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="5A:BB:CC:DD:EE:FF",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        assert raw.mac_type == "resolvable_private"

    def test_non_resolvable_private_ad(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="1A:BB:CC:DD:EE:FF",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        assert raw.mac_type == "non_resolvable_private"


class TestSerializeMacType:
    """Test that mac_type is included in WebSocket serialization."""

    def test_serialize_includes_mac_type_public(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="00:11:22:33:44:55",
            address_type="public",
            manufacturer_data=None,
            service_data=None,
        )
        serialized = _serialize(raw)
        assert serialized["mac_type"] == "public"

    def test_serialize_includes_mac_type_random_static(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="C0:11:22:33:44:55",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        serialized = _serialize(raw)
        assert serialized["mac_type"] == "random_static"

    def test_serialize_nested_in_dict(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="5A:BB:CC:DD:EE:FF",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        serialized = _serialize({"raw": raw, "info": "test"})
        assert serialized["raw"]["mac_type"] == "resolvable_private"
