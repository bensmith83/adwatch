"""Tests for the Ledger hardware-wallet plugin.

Per apk-ble-hunting/reports/ledger-live_passive.md. Ledger devices advertise a
product-family 128-bit service UUID `13d63400-2c97-XXXX-NNNN-4c6564676572`
(tail = ASCII "Ledger") plus the plain product name. No manufacturer data, no
service data, no per-unit identifier.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ledger_wallet import (
    LedgerWalletParser,
    LEDGER_SERVICE_UUIDS,
    LEDGER_NAME_RE,
    NANO_X_UUID,
    FLEX_UUID,
    STAX_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "D4:11:22:33:44:55",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="ledger_wallet",
        service_uuid=LEDGER_SERVICE_UUIDS,
        local_name_pattern=LEDGER_NAME_RE,
        description="Ledger",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(LedgerWalletParser):
        pass

    return _P


class TestLedgerMatching:
    @pytest.mark.parametrize("uuid", [NANO_X_UUID, FLEX_UUID, STAX_UUID])
    def test_matches_product_uuids(self, uuid):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[uuid]))) == 1

    def test_matches_uppercase_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[NANO_X_UUID.upper()]))) == 1

    @pytest.mark.parametrize(
        "name", ["Nano X", "Ledger Stax", "Ledger Flex", "Ledger Apex"]
    )
    def test_matches_product_names(self, name):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name=name))) == 1

    def test_does_not_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Nanoleaf Shapes", service_uuids=["fd6f"])
        assert registry.match(ad) == []


class TestLedgerParsing:
    def test_nano_x_by_uuid(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[NANO_X_UUID]))
        assert res is not None
        assert res.parser_name == "ledger_wallet"
        assert res.beacon_type == "ledger_wallet"
        assert res.device_class == "hardware_wallet"
        assert res.metadata["vendor"] == "Ledger"
        assert res.metadata["model"] == "Ledger Nano X"
        assert res.metadata["family_code"] == "0004"
        assert res.metadata["service_uuid"] == NANO_X_UUID

    def test_flex_by_uuid(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[FLEX_UUID]))
        assert res.metadata["model"] == "Ledger Flex"
        assert res.metadata["family_code"] == "3004"

    def test_stax_uuid_is_shared_with_apex(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[STAX_UUID]))
        assert res.metadata["model"] == "Ledger Stax / Apex"
        assert res.metadata["family_code"] == "6004"

    def test_name_disambiguates_shared_stax_apex_uuid(self):
        res = LedgerWalletParser().parse(
            _make_ad(service_uuids=[STAX_UUID], local_name="Ledger Apex")
        )
        assert res.metadata["model"] == "Ledger Apex"
        assert res.metadata["device_name"] == "Ledger Apex"

    def test_unknown_family_still_recognised_as_ledger(self):
        # `8004` / `9004` surfaced in the Hermes bundle but map to no product.
        uuid = "13d63400-2c97-8004-0000-4c6564676572"
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[uuid]))
        assert res is not None
        assert res.metadata["family_code"] == "8004"
        assert res.metadata["model"] == "Ledger (unknown family 8004)"

    def test_uuid_ascii_signature_recorded(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[NANO_X_UUID]))
        assert res.metadata["uuid_vendor_signature"] == "Ledger"

    def test_name_only_match(self):
        res = LedgerWalletParser().parse(_make_ad(local_name="Nano X"))
        assert res is not None
        assert res.metadata["model"] == "Ledger Nano X"
        assert res.metadata["service_uuid_match"] is False

    def test_uuid_match_flag(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[FLEX_UUID]))
        assert res.metadata["service_uuid_match"] is True

    def test_lookalike_uuid_with_wrong_tail_is_ignored(self):
        # Same 13d63400-2c97 prefix but not the ASCII "Ledger" tail.
        uuid = "13d63400-2c97-0004-0000-4c6564676573"
        assert LedgerWalletParser().parse(_make_ad(service_uuids=[uuid])) is None

    def test_unrelated_ad_returns_none(self):
        assert LedgerWalletParser().parse(_make_ad(local_name="Nanoleaf")) is None

    def test_empty_ad_returns_none(self):
        assert LedgerWalletParser().parse(_make_ad()) is None

    def test_no_telemetry_claimed(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[NANO_X_UUID]))
        assert res.raw_payload_hex == ""
        assert "battery_percent" not in res.metadata


class TestLedgerIdentity:
    def test_identity_hash_from_mac(self):
        res = LedgerWalletParser().parse(_make_ad(service_uuids=[NANO_X_UUID]))
        expected = hashlib.sha256(b"ledger:D4:11:22:33:44:55").hexdigest()[:16]
        assert res.identifier_hash == expected
        assert len(res.identifier_hash) == 16

    def test_two_units_of_same_model_differ_only_by_mac(self):
        a = LedgerWalletParser().parse(
            _make_ad(service_uuids=[NANO_X_UUID], mac_address="AA:AA:AA:AA:AA:AA")
        )
        b = LedgerWalletParser().parse(
            _make_ad(service_uuids=[NANO_X_UUID], mac_address="BB:BB:BB:BB:BB:BB")
        )
        assert a.metadata["model"] == b.metadata["model"]
        assert a.identifier_hash != b.identifier_hash

    def test_storage_schema_is_none(self):
        assert LedgerWalletParser().storage_schema() is None
