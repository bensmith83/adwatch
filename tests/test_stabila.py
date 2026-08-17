"""Tests for the STABILA laser distance measure plugin.

Per apk-ble-hunting/reports/stabila-measures_passive.md. The manufacturer- and
service-data byte layouts live in a Dart snapshot and are not recoverable, so
this is a presence/identity parser built on the custom 128-bit "Disto" service
UUID plus the advertised model name.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.stabila import (
    StabilaParser,
    STABILA_SERVICE_UUID,
    STABILA_NAME_RE,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "C0:11:22:33:44:55",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="stabila",
        service_uuid=STABILA_SERVICE_UUID,
        local_name_pattern=STABILA_NAME_RE,
        description="STABILA",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(StabilaParser):
        pass

    return _P


class TestStabilaMatching:
    def test_matches_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[STABILA_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_uppercase_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[STABILA_SERVICE_UUID.upper()])
        assert len(registry.match(ad)) == 1

    def test_matches_advertised_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Stabila LD 250 BT")
        assert len(registry.match(ad)) == 1

    def test_matches_name_case_insensitively(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="STABILA LD 520")
        assert len(registry.match(ad)) == 1

    def test_does_not_match_unrelated_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Stabilizer Pro")
        assert registry.match(ad) == []

    def test_does_not_match_unrelated_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["180f"], local_name="Random Device")
        assert registry.match(ad) == []


class TestStabilaParsing:
    def test_uuid_only_presence(self):
        res = StabilaParser().parse(_make_ad(service_uuids=[STABILA_SERVICE_UUID]))
        assert res is not None
        assert res.parser_name == "stabila"
        assert res.beacon_type == "stabila"
        assert res.device_class == "measuring_tool"
        assert res.metadata["vendor"] == "STABILA"
        assert res.metadata["service_uuid_match"] is True

    def test_model_extracted_from_name(self):
        res = StabilaParser().parse(
            _make_ad(local_name="Stabila LD 250 BT", service_uuids=[STABILA_SERVICE_UUID])
        )
        assert res.metadata["device_name"] == "Stabila LD 250 BT"
        assert res.metadata["model"] == "LD 250 BT"
        assert res.metadata["product_family"] == "LD 250 BT laser distance measure"

    def test_unknown_model_still_reported(self):
        res = StabilaParser().parse(_make_ad(local_name="Stabila LD 999 XT"))
        assert res.metadata["model"] == "LD 999 XT"
        assert "product_family" not in res.metadata

    def test_ld520_family(self):
        res = StabilaParser().parse(_make_ad(local_name="Stabila LD 520"))
        assert res.metadata["model"] == "LD 520"
        assert res.metadata["product_family"] == "LD 520 laser distance measure"

    def test_name_only_has_no_uuid_flag(self):
        res = StabilaParser().parse(_make_ad(local_name="Stabila LD 250 BT"))
        assert res.metadata["service_uuid_match"] is False

    def test_manufacturer_data_is_surfaced_undecoded(self):
        res = StabilaParser().parse(
            _make_ad(
                service_uuids=[STABILA_SERVICE_UUID],
                manufacturer_data=bytes.fromhex("ffff0102030405"),
            )
        )
        # Layout unknown (Dart snapshot) — surface raw for the explorer.
        assert res.metadata["company_id"] == 0xFFFF
        assert res.metadata["payload_hex"] == "0102030405"
        assert res.raw_payload_hex == "ffff0102030405"

    def test_service_data_length_surfaced(self):
        res = StabilaParser().parse(
            _make_ad(
                service_uuids=[STABILA_SERVICE_UUID],
                service_data={STABILA_SERVICE_UUID: b"\xaa\xbb"},
            )
        )
        assert res.metadata["service_data_hex"] == "aabb"

    def test_no_match_returns_none(self):
        assert StabilaParser().parse(_make_ad(local_name="Something Else")) is None

    def test_empty_ad_returns_none(self):
        assert StabilaParser().parse(_make_ad()) is None


class TestStabilaIdentity:
    def test_identity_hash_from_mac(self):
        res = StabilaParser().parse(_make_ad(local_name="Stabila LD 250 BT"))
        expected = hashlib.sha256(b"stabila:C0:11:22:33:44:55").hexdigest()[:16]
        assert res.identifier_hash == expected
        assert len(res.identifier_hash) == 16

    def test_storage_schema_is_none(self):
        assert StabilaParser().storage_schema() is None
