"""Tests for Tedee smart-lock plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tedee import (
    TedeeParser,
    NORDIC_SECURE_DFU_UUID,
    TEDEE_UUID_TAIL,
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
        name="tedee",
        service_uuid=NORDIC_SECURE_DFU_UUID,
        local_name_pattern=r"^Tedee( |$)",
        description="Tedee",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(TedeeParser):
        pass

    return _P


class TestTedeeMatching:
    def test_match_dfu_uuid_with_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[NORDIC_SECURE_DFU_UUID], local_name="Tedee")
        assert len(registry.match(ad)) == 1

    def test_match_local_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Tedee PRO")
        assert len(registry.match(ad)) == 1


class TestTedeeParsing:
    def test_dfu_alone_without_tedee_signal_returns_none(self):
        # Nordic DFU is shared — without Tedee name or vendor UUID, return None
        ad = _make_ad(service_uuids=[NORDIC_SECURE_DFU_UUID])
        assert TedeeParser().parse(ad) is None

    def test_dfu_mode_flag(self):
        ad = _make_ad(
            service_uuids=[NORDIC_SECURE_DFU_UUID],
            local_name="Tedee PRO",
        )
        result = TedeeParser().parse(ad)
        assert result.metadata["dfu_mode"] is True

    def test_tedee_base_uuid_detection(self):
        # Construct a UUID under the Tedee vendor base
        tedee_uuid = "abcd1234" + TEDEE_UUID_TAIL
        ad = _make_ad(service_uuids=[tedee_uuid])
        result = TedeeParser().parse(ad)
        assert result is not None
        assert result.metadata["tedee_service_handle_hex"] == "abcd1234"
        assert tedee_uuid in result.metadata["tedee_service_uuids"]

    def test_identity_uses_service_handle(self):
        tedee_uuid = "deadbeef" + TEDEE_UUID_TAIL
        ad = _make_ad(service_uuids=[tedee_uuid])
        result = TedeeParser().parse(ad)
        expected = hashlib.sha256(b"tedee:deadbeef").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_name_only_match(self):
        result = TedeeParser().parse(_make_ad(local_name="Tedee Bridge"))
        assert result is not None
        assert result.metadata["model_hint"] == "Tedee Bridge"

    def test_returns_none_for_unrelated(self):
        assert TedeeParser().parse(_make_ad(local_name="Yale")) is None
