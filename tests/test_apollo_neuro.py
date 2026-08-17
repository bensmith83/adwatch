"""Tests for the Apollo Neuro wearable plugin.

Per apk-ble-hunting/reports/apolloneuro-apollo_passive.md — the app's sole
discovery filter is ``ScanFilter.setManufacturerData(1953, null)``, i.e. SIG
company ID 0x07A1 with no data or mask. The payload is never decoded.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.apollo_neuro import ApolloNeuroParser, APOLLO_COMPANY_ID


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "F1:22:33:44:55:66",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _apollo_mfr(payload=b"\x01\x02\x03\x04"):
    """Company ID 0x07A1 little-endian (raw bytes a1 07) + payload."""
    return APOLLO_COMPANY_ID.to_bytes(2, "little") + payload


def _register(registry):
    @register_parser(
        name="apollo_neuro",
        company_id=APOLLO_COMPANY_ID,
        description="Apollo Neuro",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ApolloNeuroParser):
        pass

    return _P


class TestApolloNeuroMatching:
    def test_company_id_is_little_endian_a107(self):
        ad = _make_ad(manufacturer_data=_apollo_mfr())
        assert ad.manufacturer_data[:2] == bytes.fromhex("a107")
        assert ad.company_id == 0x07A1 == 1953

    def test_matches_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_apollo_mfr())
        assert len(registry.match(ad)) == 1

    def test_does_not_match_byteswapped_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes.fromhex("07a1") + b"\x01")
        assert registry.match(ad) == []

    def test_does_not_match_other_vendor(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes.fromhex("4c00") + b"\x01")
        assert registry.match(ad) == []


class TestApolloNeuroParsing:
    def test_parses_presence(self):
        result = ApolloNeuroParser().parse(_make_ad(manufacturer_data=_apollo_mfr()))
        assert result is not None
        assert result.parser_name == "apollo_neuro"
        assert result.beacon_type == "apollo_neuro"
        assert result.device_class == "wearable"
        assert result.metadata["vendor"] == "Apollo Neuroscience"
        assert result.metadata["company_id"] == 0x07A1

    def test_payload_surfaced_but_not_decoded(self):
        ad = _make_ad(manufacturer_data=_apollo_mfr(bytes.fromhex("deadbeef")))
        result = ApolloNeuroParser().parse(ad)
        assert result.metadata["mfr_payload_hex"] == "deadbeef"
        assert result.metadata["mfr_payload_len"] == 4
        assert result.metadata["mfr_payload_decoded"] is False

    def test_handles_empty_payload(self):
        ad = _make_ad(manufacturer_data=_apollo_mfr(b""))
        result = ApolloNeuroParser().parse(ad)
        assert result is not None
        assert result.metadata["mfr_payload_hex"] == ""
        assert result.metadata["mfr_payload_len"] == 0

    def test_notes_extended_advertising(self):
        result = ApolloNeuroParser().parse(_make_ad(manufacturer_data=_apollo_mfr()))
        assert result.metadata["extended_advertising"] is True

    def test_flags_sensitive_category(self):
        result = ApolloNeuroParser().parse(_make_ad(manufacturer_data=_apollo_mfr()))
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "stress_therapy"

    def test_no_telemetry_claimed(self):
        result = ApolloNeuroParser().parse(_make_ad(manufacturer_data=_apollo_mfr()))
        assert result.metadata["telemetry"] == "none (connect-only GATT)"

    def test_raw_payload_hex_is_full_mfr_data(self):
        ad = _make_ad(manufacturer_data=_apollo_mfr(b"\xaa"))
        assert ApolloNeuroParser().parse(ad).raw_payload_hex == "a107aa"

    def test_identity_hash_from_mac(self):
        ad = _make_ad(manufacturer_data=_apollo_mfr())
        result = ApolloNeuroParser().parse(ad)
        expected = hashlib.sha256(b"apollo_neuro:F1:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_rejects_wrong_company_id(self):
        ad = _make_ad(manufacturer_data=bytes.fromhex("4c00") + b"\x01\x02")
        assert ApolloNeuroParser().parse(ad) is None

    def test_rejects_missing_manufacturer_data(self):
        assert ApolloNeuroParser().parse(_make_ad()) is None

    def test_rejects_truncated_manufacturer_data(self):
        assert ApolloNeuroParser().parse(_make_ad(manufacturer_data=b"\xa1")) is None

    def test_storage_schema_is_none(self):
        assert ApolloNeuroParser().storage_schema() is None
