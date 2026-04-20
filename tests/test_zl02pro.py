"""Tests for ZL02PRO / DaFit-family smartwatch parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.zl02pro import (
    ZL02ProParser,
    DAFIT_SERVICE_DATA_UUID,
    DAFIT_HEADER,
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
        name="zl02pro",
        service_uuid=DAFIT_SERVICE_DATA_UUID,
        local_name_pattern=r"^ZL0[0-9A-Z]{2,}",
        description="ZL02PRO / DaFit-family cheap BT-calling smartwatch",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ZL02ProParser):
        pass

    return registry


class TestZL02ProRegistry:
    def test_matches_on_name(self):
        registry = _make_registry()
        ad = _make_ad(local_name="ZL02PRO")
        assert len(registry.match(ad)) >= 1

    def test_matches_on_service_data_uuid(self):
        """FEEA service data with DKR header should match even without a name."""
        registry = _make_registry()
        ad = _make_ad(service_data={"feea": bytes.fromhex("444b5203040010")})
        assert len(registry.match(ad)) >= 1

    def test_no_match_unrelated(self):
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherThing")
        assert len(registry.match(ad)) == 0


class TestZL02ProParser:
    def test_basic_fields(self):
        parser = ZL02ProParser()
        ad = _make_ad(
            local_name="ZL02PRO",
            service_data={"feea": bytes.fromhex("444b5203040010")},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "zl02pro"
        assert result.beacon_type == "zl02pro"
        assert result.device_class == "smartwatch"
        assert result.metadata["device_name"] == "ZL02PRO"

    def test_dkr_header_decoded(self):
        """DaFit service data begins with ASCII 'DKR' (0x44 0x4B 0x52)."""
        parser = ZL02ProParser()
        ad = _make_ad(service_data={"feea": bytes.fromhex("444b5203040010")})
        result = parser.parse(ad)
        assert result.metadata.get("protocol") == "DKR"
        # trailing bytes after DKR are opaque vendor state — stash them hex
        assert result.metadata.get("protocol_payload_hex") == "03040010"

    def test_parses_by_name_without_service_data(self):
        parser = ZL02ProParser()
        ad = _make_ad(local_name="ZL02PRO")
        result = parser.parse(ad)
        assert result is not None
        assert "protocol" not in result.metadata

    def test_identity_hash_stable(self):
        mac = "11:22:33:44:55:66"
        parser = ZL02ProParser()
        ad = _make_ad(mac_address=mac, local_name="ZL02PRO")
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:zl02pro".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_for_unrelated(self):
        parser = ZL02ProParser()
        assert parser.parse(_make_ad(local_name="Kettle")) is None

    def test_rejects_feea_without_dkr_header(self):
        """FEEA is not SIG-assigned so other devices could legally reuse it.
        Only accept when the payload begins with the DKR magic."""
        parser = ZL02ProParser()
        ad = _make_ad(service_data={"feea": bytes.fromhex("deadbeef")})
        assert parser.parse(ad) is None
