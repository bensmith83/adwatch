"""Tests for Roborock vacuum plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.roborock import (
    RoborockParser,
    ROBOROCK_STEADY_UUID,
    ROBOROCK_PROVISIONING_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="roborock",
                     service_uuid=[ROBOROCK_STEADY_UUID, ROBOROCK_PROVISIONING_UUID],
                     local_name_pattern=r"^roborock-",
                     description="Roborock", version="1.0.0", core=False,
                     registry=registry)
    class _P(RoborockParser):
        pass
    return _P


class TestRoborockMatching:
    def test_match_steady_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[ROBOROCK_STEADY_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_provisioning_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[ROBOROCK_PROVISIONING_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="roborock-s7_abc123")
        assert len(registry.match(ad)) == 1


class TestRoborockParsing:
    def test_steady_state_lifecycle(self):
        ad = _make_ad(service_uuids=[ROBOROCK_STEADY_UUID])
        result = RoborockParser().parse(ad)
        assert result is not None
        assert result.metadata["lifecycle"] == "steady_state"
        assert result.metadata["onboarded"] is True

    def test_provisioning_lifecycle(self):
        ad = _make_ad(service_uuids=[ROBOROCK_PROVISIONING_UUID])
        result = RoborockParser().parse(ad)
        assert result.metadata["lifecycle"] == "provisioning"
        assert result.metadata["onboarded"] is False

    def test_name_extracts_model_and_device_id(self):
        ad = _make_ad(local_name="roborock-s7_abc123")
        result = RoborockParser().parse(ad)
        assert result.metadata["model_token"] == "s7"
        assert result.metadata["device_identifier"] == "abc123"

    def test_name_extracts_complex_model(self):
        ad = _make_ad(local_name="roborock-s7maxv_def4567")
        result = RoborockParser().parse(ad)
        assert result.metadata["model_token"] == "s7maxv"

    def test_identity_uses_device_identifier(self):
        ad = _make_ad(local_name="roborock-s7_DEVID42",
                      mac_address="11:22:33:44:55:66")
        result = RoborockParser().parse(ad)
        expected = hashlib.sha256(b"roborock:DEVID42").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        ad = _make_ad(service_uuids=[ROBOROCK_STEADY_UUID])
        result = RoborockParser().parse(ad)
        assert result.parser_name == "roborock"
        assert result.beacon_type == "roborock"
        assert result.device_class == "vacuum"

    def test_returns_none_unrelated(self):
        assert RoborockParser().parse(_make_ad(local_name="Other")) is None
