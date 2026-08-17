"""Tests for Beurer HealthManager plugin."""

import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.beurer import (
    BeurerParser,
    BEURER_COMPANY_ID,
    BEURER_SCALE_UUID, BEURER_BP_OXIMETER_UUID,
    BEURER_CUSTOM_128_UUID,
    ALL_BEURER_UUIDS,
    BEURER_NAME_PATTERN,
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
        name="beurer",
        company_id=BEURER_COMPANY_ID,
        service_uuid=ALL_BEURER_UUIDS,
        local_name_pattern=r"(?i)^(BM|BC|BF|AS|GL|PO|DELUXE|PREMIUM|SERIES|ELITE|SENSE|Beurer)",
        description="Beurer",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(BeurerParser):
        pass
    return _P


def _mfr_with_mac(mac_bytes: bytes) -> bytes:
    """Build mfr-data with CID + 4 prefix bytes + 0xFF sentinel + 4 reserved + 6-byte MAC."""
    cid = struct.pack("<H", BEURER_COMPANY_ID)
    return cid + b"\x00\x01\x02\x03" + b"\xff" + b"\x00\x00\x00\x00" + mac_bytes


class TestBeurerMatching:
    def test_match_scale_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BEURER_SCALE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_bp_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BEURER_BP_OXIMETER_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_custom_128(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BEURER_CUSTOM_128_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_bm_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="BM27")
        assert len(registry.match(ad)) == 1


class TestBeurerProductFamily:
    def test_bm_is_bp_monitor(self):
        result = BeurerParser().parse(_make_ad(local_name="BM27"))
        assert result.metadata["product_family"] == "blood_pressure_monitor"

    def test_bc_is_body_composition_scale(self):
        result = BeurerParser().parse(_make_ad(local_name="BC54W"))
        assert result.metadata["product_family"] == "body_composition_scale"

    def test_po_is_pulse_oximeter(self):
        result = BeurerParser().parse(_make_ad(local_name="PO60"))
        assert result.metadata["product_family"] == "pulse_oximeter"

    def test_deluxe_is_rebrand(self):
        result = BeurerParser().parse(_make_ad(local_name="DELUXE600"))
        assert result.metadata["product_family"] == "rebrand_flagship"


class TestBeurerScaleMacExtraction:
    def test_mac_extracted_after_sentinel(self):
        # Six MAC bytes — MAC stored little-endian on wire, reversed for display
        mac_le = bytes.fromhex("ffeeddccbbaa")
        ad = _make_ad(manufacturer_data=_mfr_with_mac(mac_le))
        result = BeurerParser().parse(ad)
        assert result.metadata["device_mac_in_mfr"] == "AA:BB:CC:DD:EE:FF"


class TestBeurerBasics:
    def test_returns_none_unrelated(self):
        assert BeurerParser().parse(_make_ad(local_name="iPhone")) is None

    def test_parse_basics(self):
        result = BeurerParser().parse(_make_ad(local_name="BM27"))
        assert result.parser_name == "beurer"
        assert result.device_class == "medical"


class TestBeurerNamePrefixGating:
    """The two-letter model prefixes must be followed by a digit.

    `NAME_FAMILY_RULES` already requires `^PO\\d` etc.; without the same
    constraint on the match gate, `^PO` claimed unrelated devices such as the
    Therabody `PowerDot2-…` EMS pod (and would claim `Polar`, `Pod`, …).
    """

    def test_powerdot_is_not_a_beurer(self):
        assert BeurerParser().parse(_make_ad(local_name="PowerDot2-4F21")) is None

    def test_polar_is_not_a_beurer(self):
        assert BeurerParser().parse(_make_ad(local_name="Polar H10")) is None

    def test_asics_is_not_a_beurer(self):
        assert BeurerParser().parse(_make_ad(local_name="ASICS Runner")) is None

    def test_real_model_codes_still_match(self):
        for name in ("BM27", "BC54W", "BF700", "AS99", "GL50", "PO60"):
            result = BeurerParser().parse(_make_ad(local_name=name))
            assert result is not None, name
            assert result.metadata["model_code"] == name

    def test_word_prefixes_still_match_without_a_digit(self):
        for name in ("DELUXE600", "PREMIUM", "Beurer Scale"):
            assert BeurerParser().parse(_make_ad(local_name=name)) is not None, name

    def test_registry_pattern_matches_the_parse_gate(self):
        registry = ParserRegistry()

        @register_parser(
            name="beurer", company_id=BEURER_COMPANY_ID,
            service_uuid=ALL_BEURER_UUIDS,
            local_name_pattern=BEURER_NAME_PATTERN,
            description="Beurer", version="1.0.0", core=False, registry=registry,
        )
        class _P(BeurerParser):
            pass

        assert registry.match(_make_ad(local_name="PowerDot2-4F21")) == []
        assert len(registry.match(_make_ad(local_name="BM27"))) == 1
