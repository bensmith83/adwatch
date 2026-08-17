"""Tests for the Trezor hardware-wallet plugin.

Per apk-ble-hunting/reports/trezor-suite_passive.md. Trezor Safe devices
advertise the open-source THP service UUID `8c000001-a59b-4d58-a9ad-073df69fa1b1`
and a device-class-only name. No manufacturer data, no service data, no
per-unit identifier — deliberately.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.trezor_wallet import (
    TrezorWalletParser,
    TREZOR_SERVICE_UUID,
    TREZOR_NAME_RE,
    TREZOR_COMPANY_ID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "E1:22:33:44:55:66",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="trezor_wallet",
        company_id=TREZOR_COMPANY_ID,
        service_uuid=TREZOR_SERVICE_UUID,
        local_name_pattern=TREZOR_NAME_RE,
        description="Trezor",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(TrezorWalletParser):
        pass

    return _P


ALL_NAMES = [
    "Trezor Safe 3",
    "Trezor Safe 5",
    "Trezor Safe 5 Freedom Edition",
    "Trezor Safe 7",
    "Trezor Safe 7 Freedom Edition",
]


class TestTrezorMatching:
    def test_matches_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[TREZOR_SERVICE_UUID]))) == 1

    def test_matches_uppercase_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TREZOR_SERVICE_UUID.upper()])
        assert len(registry.match(ad)) == 1

    @pytest.mark.parametrize("name", ALL_NAMES)
    def test_matches_documented_names(self, name):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name=name))) == 1

    def test_matches_trezor_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        # 0x0F29 little-endian = 29 0f
        ad = _make_ad(manufacturer_data=bytes.fromhex("290f0102"))
        assert len(registry.match(ad)) == 1

    def test_does_not_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Safe 7", service_uuids=["180f"])
        assert registry.match(ad) == []


class TestTrezorParsing:
    def test_uuid_only(self):
        res = TrezorWalletParser().parse(_make_ad(service_uuids=[TREZOR_SERVICE_UUID]))
        assert res is not None
        assert res.parser_name == "trezor_wallet"
        assert res.beacon_type == "trezor_wallet"
        assert res.device_class == "hardware_wallet"
        assert res.metadata["vendor"] == "Trezor"
        assert res.metadata["service_uuid_match"] is True
        assert "model" not in res.metadata

    @pytest.mark.parametrize(
        "name,model,freedom",
        [
            ("Trezor Safe 3", "Trezor Safe 3", False),
            ("Trezor Safe 5", "Trezor Safe 5", False),
            ("Trezor Safe 5 Freedom Edition", "Trezor Safe 5", True),
            ("Trezor Safe 7", "Trezor Safe 7", False),
            ("Trezor Safe 7 Freedom Edition", "Trezor Safe 7", True),
        ],
    )
    def test_model_and_edition(self, name, model, freedom):
        res = TrezorWalletParser().parse(
            _make_ad(local_name=name, service_uuids=[TREZOR_SERVICE_UUID])
        )
        assert res.metadata["model"] == model
        assert res.metadata["freedom_edition"] is freedom
        assert res.metadata["device_name"] == name

    def test_unknown_trezor_name_still_matches(self):
        res = TrezorWalletParser().parse(_make_ad(local_name="Trezor Model T"))
        assert res is not None
        assert res.metadata["device_name"] == "Trezor Model T"
        assert "model" not in res.metadata
        assert res.metadata["service_uuid_match"] is False

    def test_manufacturer_data_surfaced_undecoded(self):
        # The report says Trezor emits none; if one ever does, don't drop it.
        res = TrezorWalletParser().parse(
            _make_ad(manufacturer_data=bytes.fromhex("290faabbcc"))
        )
        assert res is not None
        assert res.metadata["company_id"] == TREZOR_COMPANY_ID
        assert res.metadata["payload_hex"] == "aabbcc"
        assert res.raw_payload_hex == "290faabbcc"

    def test_other_company_id_alone_is_ignored(self):
        assert TrezorWalletParser().parse(
            _make_ad(manufacturer_data=bytes.fromhex("4c000102"))
        ) is None

    def test_unrelated_ad_returns_none(self):
        assert TrezorWalletParser().parse(_make_ad(local_name="Safe 7")) is None

    def test_empty_ad_returns_none(self):
        assert TrezorWalletParser().parse(_make_ad()) is None

    def test_no_telemetry_claimed(self):
        res = TrezorWalletParser().parse(_make_ad(service_uuids=[TREZOR_SERVICE_UUID]))
        assert res.raw_payload_hex == ""
        assert "battery_percent" not in res.metadata


class TestTrezorIdentity:
    def test_identity_hash_from_mac(self):
        res = TrezorWalletParser().parse(_make_ad(service_uuids=[TREZOR_SERVICE_UUID]))
        expected = hashlib.sha256(b"trezor:E1:22:33:44:55:66").hexdigest()[:16]
        assert res.identifier_hash == expected
        assert len(res.identifier_hash) == 16

    def test_identical_units_differ_only_by_mac(self):
        a = TrezorWalletParser().parse(
            _make_ad(local_name="Trezor Safe 7", mac_address="AA:AA:AA:AA:AA:AA")
        )
        b = TrezorWalletParser().parse(
            _make_ad(local_name="Trezor Safe 7", mac_address="BB:BB:BB:BB:BB:BB")
        )
        assert a.metadata["model"] == b.metadata["model"]
        assert a.identifier_hash != b.identifier_hash

    def test_storage_schema_is_none(self):
        assert TrezorWalletParser().storage_schema() is None
