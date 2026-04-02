"""Tests for Meshtastic BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.meshtastic import MeshtasticParser, MESHTASTIC_SERVICE_UUID


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
        name="meshtastic",
        service_uuid=MESHTASTIC_SERVICE_UUID,
        local_name_pattern=r"^Meshtastic_",
        description="Meshtastic mesh networking advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(MeshtasticParser):
        pass

    return registry


class TestMeshtasticRegistry:
    def test_matches_service_uuid(self):
        """Matches when service_uuids contains the Meshtastic UUID."""
        registry = _make_registry()
        ad = _make_ad(
            service_uuids=["6ba1b218-15a8-461f-9fa8-5dcae273eafd"],
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name 'Meshtastic_bb14' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="Meshtastic_bb14")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestMeshtasticParser:
    def test_parser_name(self):
        """parser_name is 'meshtastic'."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_bb14")
        result = parser.parse(ad)
        assert result.parser_name == "meshtastic"

    def test_beacon_type(self):
        """beacon_type is 'meshtastic'."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_bb14")
        result = parser.parse(ad)
        assert result.beacon_type == "meshtastic"

    def test_device_class(self):
        """device_class is 'mesh_node'."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_bb14")
        result = parser.parse(ad)
        assert result.device_class == "mesh_node"

    def test_node_id_extraction(self):
        """'Meshtastic_bb14' -> metadata['node_id'] == 'bb14'."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_bb14")
        result = parser.parse(ad)
        assert result.metadata["node_id"] == "bb14"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'Meshtastic_bb14'."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_bb14")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Meshtastic_bb14"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:meshtastic)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_bb14", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:meshtastic".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_service_uuid_match_without_name(self):
        """Parses with service_uuid match even when local_name is None."""
        parser = MeshtasticParser()
        ad = _make_ad(
            service_uuids=["6ba1b218-15a8-461f-9fa8-5dcae273eafd"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "meshtastic"
        assert "node_id" not in result.metadata

    def test_local_name_match_without_uuid(self):
        """Parses with local_name match even without service_uuids."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="Meshtastic_a1b2")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["node_id"] == "a1b2"

    def test_returns_none_no_match(self):
        """Returns None for unrelated advertisement."""
        parser = MeshtasticParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name_no_uuid(self):
        """Returns None for ad with no local_name and no matching service UUID."""
        parser = MeshtasticParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
