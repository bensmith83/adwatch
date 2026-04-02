"""Tests for Google Nearby Share / Quick Share BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.google_nearby_share import (
    GoogleNearbyShareParser,
    NEARBY_SHARE_UUID,
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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="google_nearby_share",
        service_uuid=NEARBY_SHARE_UUID,
        description="Google Nearby Share / Quick Share",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GoogleNearbyShareParser):
        pass

    return registry


class TestGoogleNearbyShareRegistry:
    def test_matches_service_uuid(self):
        """Matches when service_data contains fdf7."""
        registry = _make_registry()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"})
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestGoogleNearbyShareParser:
    def test_parser_name(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"})
        result = parser.parse(ad)
        assert result.parser_name == "google_nearby_share"

    def test_beacon_type(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"})
        result = parser.parse(ad)
        assert result.beacon_type == "google_nearby_share"

    def test_device_type_phone(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x01"})
        result = parser.parse(ad)
        assert result.device_class == "phone"
        assert result.metadata["device_type"] == "phone"

    def test_device_type_tablet(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x02"})
        result = parser.parse(ad)
        assert result.device_class == "tablet"
        assert result.metadata["device_type"] == "tablet"

    def test_device_type_laptop(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"})
        result = parser.parse(ad)
        assert result.device_class == "laptop"
        assert result.metadata["device_type"] == "laptop"

    def test_device_type_unknown_defaults_phone(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\xff"})
        result = parser.parse(ad)
        assert result.device_class == "phone"
        assert result.metadata["device_type"] == "unknown"

    def test_identity_hash(self):
        mac = "11:22:33:44:55:66"
        parser = GoogleNearbyShareParser()
        ad = _make_ad(
            mac_address=mac,
            service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"},
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:google_nearby_share".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_no_service_data(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_wrong_uuid(self):
        parser = GoogleNearbyShareParser()
        ad = _make_ad(service_data={"feaf": b"\x01\x02\x03"})
        result = parser.parse(ad)
        assert result is None

    def test_rejects_bose_company_id(self):
        """Returns None when Bose company_id 0x0065 is present."""
        parser = GoogleNearbyShareParser()
        bose_mfr = (0x0065).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(
            manufacturer_data=bose_mfr,
            service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"},
        )
        result = parser.parse(ad)
        assert result is None

    def test_rejects_bose_fe78_service_uuid(self):
        """Returns None when Bose service UUID fe78 is in service_data."""
        parser = GoogleNearbyShareParser()
        ad = _make_ad(
            service_data={
                "fdf7": b"\x01" + b"\x00" * 20 + b"\x03",
                "fe78": b"\x01\x02",
            },
        )
        result = parser.parse(ad)
        assert result is None

    def test_rejects_bose_fe78_in_service_uuids(self):
        """Returns None when Bose service UUID fe78 is in service_uuids."""
        parser = GoogleNearbyShareParser()
        ad = _make_ad(
            service_data={"fdf7": b"\x01" + b"\x00" * 20 + b"\x03"},
            service_uuids=["fe78"],
        )
        result = parser.parse(ad)
        assert result is None

    def test_payload_hex_in_metadata(self):
        parser = GoogleNearbyShareParser()
        data = b"\x01" + b"\xab" * 20 + b"\x03"
        ad = _make_ad(service_data={"fdf7": data})
        result = parser.parse(ad)
        assert result.metadata["payload_hex"] == data.hex()
