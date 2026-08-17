"""Tests for the Tomofun Furbo pet-camera plugin.

Source: apk-ble-hunting/reports/tomofun-furbo_passive.md — discovery is
name-prefix only (no mfr data, no service data, no service UUID in the AD).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.furbo import (
    FurboParser,
    FURBO_NAME_PATTERN,
    FURBO_PREFIXES,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="furbo",
        local_name_pattern=FURBO_NAME_PATTERN,
        description="Furbo",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(FurboParser):
        pass

    return _P


class TestFurboMatching:
    @pytest.mark.parametrize(
        "name",
        [
            "Furbo-N",
            "Furbo3-N-S3",
            "Furbo3C-N",
            "M2-1234567-N",
            "M3-1234567-N",
            "MINICAM0001",
            "F2-N",
        ],
    )
    def test_matches_known_shapes(self, name):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name=name))) == 1

    def test_all_seven_prefixes_declared(self):
        assert [p for p, *_ in FURBO_PREFIXES] == [
            "Furbo3C", "Furbo3", "Furbo", "MINICAM", "M3-", "M2-", "F2"
        ]

    def test_f2_length_cap_enforced(self):
        # "F2" is only 2 chars; the app caps the whole name at <5, so a long
        # name starting with F2 must not be claimed.
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="F2SomeOtherDevice")) == []

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="Fitbit Charge")) == []
        assert registry.match(_make_ad(local_name="turboMini")) == []


class TestFurboGeneration:
    def test_s3_suffix_is_v4(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo3-N-S3"))
        assert result.metadata["generation"] == "V4"

    def test_fw3_infix_is_v3(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo3FW3"))
        assert result.metadata["generation"] == "V3"

    def test_classic_furbo_is_v2(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo-N"))
        assert result.metadata["generation"] == "V2"

    def test_furbo3_prefix_defaults_to_v3(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo3-N"))
        assert result.metadata["generation"] == "V3"

    def test_mini2_is_v2_mini3_is_v3(self):
        assert FurboParser().parse(
            _make_ad(local_name="M2-1234567")
        ).metadata["generation"] == "V2"
        assert FurboParser().parse(
            _make_ad(local_name="M3-1234567")
        ).metadata["generation"] == "V3"


class TestFurboParsing:
    def test_basics(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo3-N-S3"))
        assert result is not None
        assert result.parser_name == "furbo"
        assert result.beacon_type == "furbo"
        assert result.device_class == "camera"
        assert result.metadata["vendor"] == "Tomofun"

    @pytest.mark.parametrize(
        "name,model",
        [
            ("Furbo3C-N", "Furbo 3C"),
            ("Furbo3-N", "Furbo 3"),
            ("Furbo-N", "Furbo"),
            ("MINICAM0001", "Furbo Mini Cam"),
            ("M3-1234567", "Furbo Mini 3"),
            ("M2-1234567", "Furbo Mini 2"),
            ("F2-N", "Furbo"),
        ],
    )
    def test_model_mapping(self, name, model):
        assert FurboParser().parse(_make_ad(local_name=name)).metadata["model"] == model

    def test_normal_mode_marker(self):
        assert FurboParser().parse(
            _make_ad(local_name="Furbo-N")
        ).metadata["normal_mode"] is True
        assert FurboParser().parse(
            _make_ad(local_name="MINICAM0001")
        ).metadata["normal_mode"] is False

    def test_per_unit_suffix_extracted(self):
        result = FurboParser().parse(_make_ad(local_name="M3-1234567-N"))
        assert result.metadata["unit_suffix"] == "1234567"

    def test_no_per_unit_suffix_when_name_is_generic(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo-N"))
        assert result.metadata["unit_suffix"] == ""
        assert result.metadata["identity_basis"] == "mac"

    def test_identity_from_name_when_suffix_present(self):
        a = FurboParser().parse(_make_ad(local_name="M3-1234567-N"))
        b = FurboParser().parse(
            _make_ad(local_name="M3-1234567-N", mac_address="11:22:33:44:55:66")
        )
        assert a.metadata["identity_basis"] == "name"
        assert a.identifier_hash == b.identifier_hash
        assert a.identifier_hash == hashlib.sha256(
            b"furbo:M3-1234567-N"
        ).hexdigest()[:16]
        assert a.stable_key == "furbo:M3-1234567-N"

    def test_identity_from_mac_when_no_suffix(self):
        result = FurboParser().parse(_make_ad(local_name="Furbo-N"))
        assert result.identifier_hash == hashlib.sha256(
            b"furbo:mac:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]
        assert result.stable_key is None

    def test_app_device_id_derivation(self):
        # V3/V4 take the LAST 12 alphanumeric-or-dash chars; V2 the FIRST 12.
        v34 = FurboParser().parse(_make_ad(local_name="M3-1234567-N"))
        assert v34.metadata["app_device_id"] == "M3-1234567-N"
        v2 = FurboParser().parse(_make_ad(local_name="MINICAM000123456"))
        assert v2.metadata["app_device_id"] == "MINICAM00012"

    def test_short_trailing_chars_are_not_a_unit_id(self):
        # The classic Furbo name carries at most 2 trailing chars -- too
        # little entropy to key an identity on.
        result = FurboParser().parse(_make_ad(local_name="Furbo12"))
        assert result.metadata["unit_suffix"] == "12"
        assert result.metadata["identity_basis"] == "mac"

    def test_returns_none_without_name(self):
        assert FurboParser().parse(_make_ad()) is None

    def test_returns_none_on_long_f2_name(self):
        assert FurboParser().parse(_make_ad(local_name="F2SomeOtherDevice")) is None
