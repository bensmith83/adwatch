"""Tests for Sphero robot BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.sphero import SpherParser, SPHERO_SERVICE_UUID, SPHERO_NAME_RE


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
        name="sphero",
        service_uuid=SPHERO_SERVICE_UUID,
        local_name_pattern=r"^SB-[A-F0-9]{4}$",
        description="Sphero robot advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(SpherParser):
        pass

    return registry


class TestSpheroMatching:
    def test_matches_service_uuid(self):
        """Matches on Sphero service UUID."""
        registry = _make_registry()
        ad = _make_ad(
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
            local_name="SB-9B13",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_pattern(self):
        """Matches on SB-XXXX local name."""
        registry = _make_registry()
        ad = _make_ad(local_name="SB-9B13")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_unrelated_device(self):
        """Does not match unrelated devices."""
        parser = SpherParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_no_match_no_name_no_uuid(self):
        """Does not match when no name and no UUID."""
        parser = SpherParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None


class TestSpheroParsing:
    def test_parse_basic(self):
        """Parses Sphero bolt with UUID and name."""
        parser = SpherParser()
        ad = _make_ad(
            local_name="SB-9B13",
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "sphero"
        assert result.beacon_type == "sphero"
        assert result.device_class == "toy"

    def test_device_id_from_name(self):
        """Extracts device ID from local name suffix."""
        parser = SpherParser()
        ad = _make_ad(
            local_name="SB-A6B9",
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
        )
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "A6B9"

    def test_device_name_in_metadata(self):
        """Full device name stored in metadata."""
        parser = SpherParser()
        ad = _make_ad(
            local_name="SB-2C30",
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
        )
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "SB-2C30"

    def test_identity_hash(self):
        """Identity hash is SHA256('sphero:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = SpherParser()
        ad = _make_ad(
            local_name="SB-9B13",
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"sphero:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_uuid_only_match(self):
        """Matches on UUID alone without local name."""
        parser = SpherParser()
        ad = _make_ad(
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
        )
        result = parser.parse(ad)
        assert result is not None

    def test_name_only_match(self):
        """Matches on SB- name alone without UUID."""
        parser = SpherParser()
        ad = _make_ad(local_name="SB-BF86")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_id"] == "BF86"

    def test_model_metadata(self):
        """Model is 'BOLT' for SB- prefix devices."""
        parser = SpherParser()
        ad = _make_ad(
            local_name="SB-9B13",
            service_uuids=["00010001-574f-4f20-5370-6865726f2121"],
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BOLT"
