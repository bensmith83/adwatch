"""Tests for the NeuroMetrix Quell TENS plugin.

Per apk-ble-hunting/reports/neurometrix-quell_passive.md — discovery is by the
Quell 128-bit vendor service UUID on the base
``75000d1f-XXXX-40f7-8204-ee627068ec88``. The 16-bit anchor could not be pinned
from the decompile (``BluetoothCommon`` failed jadx); ``0x1000`` is the likely
value, so the plugin registers that anchor but accepts any anchor on the base.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.quell import (
    QuellParser,
    QUELL_SERVICE_UUID,
    QUELL_NAME_PATTERN,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "00:1B:66:AA:BB:CC",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="quell",
        service_uuid=QUELL_SERVICE_UUID,
        local_name_pattern=QUELL_NAME_PATTERN,
        description="Quell",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(QuellParser):
        pass

    return _P


class TestQuellMatching:
    def test_matches_registered_anchor_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[QUELL_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Quell 2.0"))) == 1

    def test_does_not_match_unrelated_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000180f-0000-1000-8000-00805f9b34fb"])
        assert registry.match(ad) == []


class TestQuellParsing:
    def test_parses_vendor_uuid(self):
        ad = _make_ad(service_uuids=[QUELL_SERVICE_UUID])
        result = QuellParser().parse(ad)
        assert result is not None
        assert result.parser_name == "quell"
        assert result.beacon_type == "quell"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "NeuroMetrix"
        assert result.metadata["product"] == "Quell TENS"
        assert result.metadata["confidence"] == "high"

    def test_accepts_any_anchor_on_the_vendor_base(self):
        """The 16-bit anchor is unconfirmed; the 128-bit base is the signal."""
        ad = _make_ad(service_uuids=["75000d1f-2b07-40f7-8204-ee627068ec88"])
        result = QuellParser().parse(ad)
        assert result is not None
        assert result.metadata["service_uuid_anchor"] == "2b07"

    def test_records_registered_anchor(self):
        ad = _make_ad(service_uuids=[QUELL_SERVICE_UUID])
        result = QuellParser().parse(ad)
        assert result.metadata["service_uuid_anchor"] == "1000"

    def test_uuid_match_is_case_insensitive(self):
        ad = _make_ad(service_uuids=["75000D1F-1000-40F7-8204-EE627068EC88"])
        assert QuellParser().parse(ad) is not None

    def test_name_only_match_is_lower_confidence(self):
        result = QuellParser().parse(_make_ad(local_name="Quell"))
        assert result is not None
        assert result.metadata["confidence"] == "low"
        assert result.metadata["match_basis"] == "local_name"

    def test_uuid_match_basis(self):
        ad = _make_ad(service_uuids=[QUELL_SERVICE_UUID])
        assert QuellParser().parse(ad).metadata["match_basis"] == "service_uuid"

    def test_surfaces_company_id_without_decoding_payload(self):
        """The app reads the CID but never decodes the payload — nor do we."""
        ad = _make_ad(
            service_uuids=[QUELL_SERVICE_UUID],
            manufacturer_data=bytes.fromhex("cb0e11223344"),
        )
        result = QuellParser().parse(ad)
        assert result.metadata["company_id"] == 0x0ECB
        assert result.metadata["mfr_payload_hex"] == "11223344"
        assert result.metadata["mfr_payload_decoded"] is False

    def test_flags_sensitive_category(self):
        ad = _make_ad(service_uuids=[QUELL_SERVICE_UUID])
        result = QuellParser().parse(ad)
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "chronic_pain_therapy"

    def test_identity_hash_from_mac(self):
        ad = _make_ad(service_uuids=[QUELL_SERVICE_UUID])
        result = QuellParser().parse(ad)
        expected = hashlib.sha256(b"quell:00:1B:66:AA:BB:CC").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_rejects_similar_but_different_base(self):
        ad = _make_ad(service_uuids=["75000d1f-1000-40f7-8204-ee627068ec89"])
        assert QuellParser().parse(ad) is None

    def test_rejects_empty_ad(self):
        assert QuellParser().parse(_make_ad()) is None

    def test_storage_schema_is_none(self):
        assert QuellParser().storage_schema() is None
