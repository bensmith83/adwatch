"""Tests for the Anova appliance plugin.

Covers the sous-vide circulator shape from
`anovaculinary-android_passive.md` plus the product-line classification
added from `anovaculinary-anovaoven_passive.md` (whose BLE UUIDs / mfr-data
are Hermes-bytecoded and not statically recoverable -- the product-name
vocabulary is the only usable artifact in that report).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.anova import (
    AnovaParser,
    ANOVA_UUID_NEURON,
    ANOVA_UUID_SDK,
    ANOVA_NAME_PATTERN,
    PRODUCT_LINE_OVEN,
    PRODUCT_LINE_SOUS_VIDE,
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


def _registry():
    registry = ParserRegistry()

    @register_parser(
        name="anova",
        service_uuid=[ANOVA_UUID_NEURON, ANOVA_UUID_SDK],
        local_name_pattern=ANOVA_NAME_PATTERN,
        description="Anova",
        version="1.1.0",
        core=False,
        registry=registry,
    )
    class TestParser(AnovaParser):
        pass

    return registry


class TestAnovaMatching:
    def test_matches_neuron_uuid(self):
        ad = _make_ad(service_uuids=[ANOVA_UUID_NEURON])
        assert len(_registry().match(ad)) == 1

    def test_matches_sdk_uuid(self):
        ad = _make_ad(service_uuids=[ANOVA_UUID_SDK])
        assert len(_registry().match(ad)) == 1

    def test_matches_name_case_insensitively(self):
        ad = _make_ad(local_name="anova precision cooker")
        assert len(_registry().match(ad)) == 1

    def test_does_not_match_unrelated(self):
        ad = _make_ad(local_name="Some Kettle")
        assert _registry().match(ad) == []

    def test_parse_returns_none_for_unrelated(self):
        assert AnovaParser().parse(_make_ad(local_name="Some Kettle")) is None


class TestAnovaProductLine:
    def test_uuid_only_stays_generic_appliance(self):
        result = AnovaParser().parse(_make_ad(service_uuids=[ANOVA_UUID_NEURON]))
        assert result is not None
        assert result.device_class == "appliance"
        assert result.metadata["has_anova_service"] is True
        assert result.metadata["vendor"] == "Anova"

    @pytest.mark.parametrize("name", [
        "Anova Precision Oven",
        "Anova Precision Oven 1",
        "Anova Precision Oven 2",
        "anova precision oven",
    ])
    def test_oven_names_classified_as_oven(self, name):
        result = AnovaParser().parse(_make_ad(local_name=name))
        assert result is not None
        assert result.device_class == "oven"
        assert result.metadata["product_line"] == PRODUCT_LINE_OVEN
        assert result.metadata["model"] == "Anova Precision Oven"

    @pytest.mark.parametrize("name", [
        "Anova Precision Cooker",
        "Anova Precision Cooker Nano",
        "Anova Nano",
    ])
    def test_circulator_names_classified_as_sous_vide(self, name):
        result = AnovaParser().parse(_make_ad(local_name=name))
        assert result is not None
        assert result.device_class == "appliance"
        assert result.metadata["product_line"] == PRODUCT_LINE_SOUS_VIDE

    def test_unknown_anova_name_has_no_product_line(self):
        result = AnovaParser().parse(_make_ad(local_name="Anova-1234"))
        assert result is not None
        assert result.device_class == "appliance"
        assert "product_line" not in result.metadata
        assert result.metadata["device_name"] == "Anova-1234"


class TestAnovaIdentity:
    def test_identity_hash_from_mac(self):
        ad = _make_ad(local_name="Anova Precision Oven", mac_address="11:22:33:44:55:66")
        result = AnovaParser().parse(ad)
        expected = hashlib.sha256(b"anova:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self):
        result = AnovaParser().parse(_make_ad(service_uuids=[ANOVA_UUID_SDK]))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_parser_fields(self):
        result = AnovaParser().parse(_make_ad(local_name="Anova Precision Oven"))
        assert result.parser_name == "anova"
        assert result.beacon_type == "anova"
