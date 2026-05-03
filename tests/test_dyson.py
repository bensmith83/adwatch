"""Tests for Dyson connected-product plugin.

Layouts per apk-ble-hunting/reports/dyson-mobile-android_passive.md.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.dyson import (
    DysonParser,
    DYSON_COMPANY_ID,
    DYSON_AUTH_SERVICE_UUID,
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


def _register(registry):
    @register_parser(
        name="dyson",
        company_id=DYSON_COMPANY_ID,
        service_uuid=DYSON_AUTH_SERVICE_UUID,
        local_name_pattern=r"^Dyson ",
        description="Dyson",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(DysonParser):
        pass

    return _P


def _mfr(payload: bytes) -> bytes:
    return struct.pack("<H", DYSON_COMPANY_ID) + payload


class TestDysonConstants:
    def test_company_id(self):
        assert DYSON_COMPANY_ID == 0x0A12

    def test_auth_uuid(self):
        assert DYSON_AUTH_SERVICE_UUID.startswith("2dd10010")


class TestDysonMatching:
    def test_match_unprovisioned_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[DYSON_AUTH_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_post_provisioning_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(b"\x01\x01\xab\xcd"))
        assert len(registry.match(ad)) == 1

    def test_match_local_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Dyson V15 Detect")
        assert len(registry.match(ad)) == 1


class TestDysonParsing:
    def _parse(self, **kw):
        return DysonParser().parse(_make_ad(**kw))

    def test_unprovisioned_state(self):
        result = self._parse(service_uuids=[DYSON_AUTH_SERVICE_UUID])
        assert result.metadata["state"] == "unprovisioned"
        assert result.metadata["auth_service_advertised"] is True

    def test_provisioned_beacon_prefix(self):
        result = self._parse(manufacturer_data=_mfr(b"\x01\x01\xab\xcd\xef"))
        assert result.metadata["state"] == "provisioned_beacon"
        assert result.metadata["beacon_prefix_match"] is True
        assert result.metadata["state_bytes_hex"] == "abcdef"

    def test_provisioned_beacon_wrong_prefix(self):
        result = self._parse(manufacturer_data=_mfr(b"\x02\x02"))
        assert result.metadata["beacon_prefix_match"] is False
        # state should not be set when prefix doesn't match
        assert "state" not in result.metadata

    def test_model_hint_from_name(self):
        result = self._parse(local_name="Dyson V15 Detect")
        assert result.metadata["model_hint"] == "V15 Detect"

    def test_returns_none_for_unrelated(self):
        assert self._parse(local_name="SomeDevice") is None

    def test_parse_result_basics(self):
        result = self._parse(local_name="Dyson Pure Cool")
        assert result.parser_name == "dyson"
        assert result.beacon_type == "dyson"
        assert result.device_class == "appliance"
