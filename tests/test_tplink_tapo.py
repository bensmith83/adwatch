"""Tests for TP-Link Tapo/Kasa BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tplink_tapo import TpLinkTapoParser


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="tplink_tapo",
        local_name_pattern=r"(?i)^(Tapo|Kasa|TP-LINK)",
        description="TP-Link Tapo/Kasa smart home advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(TpLinkTapoParser):
        pass

    return registry


class TestTpLinkTapoRegistry:
    def test_matches_tapo_local_name(self):
        """Matches on local_name starting with 'Tapo'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_kasa_local_name(self):
        """Matches on local_name starting with 'Kasa'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Kasa_KP115")
        matches = registry.match(ad)
        assert len(matches) >= 1


class TestTpLinkTapoParser:
    def test_parser_name(self):
        """parser_name is 'tplink_tapo'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.parser_name == "tplink_tapo"

    def test_beacon_type(self):
        """beacon_type is 'tplink_tapo'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.beacon_type == "tplink_tapo"

    def test_device_class(self):
        """device_class is 'smart_home'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.device_class == "smart_home"

    # --- Product line detection ---

    def test_product_line_tapo(self):
        """Tapo_P100 -> product_line='Tapo'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100")
        result = parser.parse(ad)
        assert result.metadata["product_line"] == "Tapo"

    def test_product_line_kasa(self):
        """Kasa_KP115 -> product_line='Kasa'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Kasa_KP115")
        result = parser.parse(ad)
        assert result.metadata["product_line"] == "Kasa"

    def test_product_line_tplink(self):
        """TP-LINK_Device -> product_line='TP-Link'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="TP-LINK_Device")
        result = parser.parse(ad)
        assert result.metadata["product_line"] == "TP-Link"

    # --- Category detection from model prefix ---

    def test_category_smart_plug(self):
        """P prefix -> category='smart_plug'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.metadata["category"] == "smart_plug"

    def test_category_smart_bulb(self):
        """L prefix -> category='smart_bulb'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_L530E")
        result = parser.parse(ad)
        assert result.metadata["category"] == "smart_bulb"

    def test_category_camera(self):
        """C prefix -> category='camera'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_C200")
        result = parser.parse(ad)
        assert result.metadata["category"] == "camera"

    def test_category_hub(self):
        """H prefix -> category='hub'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_H100")
        result = parser.parse(ad)
        assert result.metadata["category"] == "hub"

    def test_category_sensor(self):
        """T prefix -> category='sensor'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_T310")
        result = parser.parse(ad)
        assert result.metadata["category"] == "sensor"

    def test_category_unknown_prefix(self):
        """Unknown model prefix -> category='smart_home'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_XYZ")
        result = parser.parse(ad)
        assert result.metadata["category"] == "smart_home"

    def test_category_no_model(self):
        """Tapo with no model -> category='smart_home'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo")
        result = parser.parse(ad)
        assert result.metadata["category"] == "smart_home"

    # --- Model extraction ---

    def test_model_extraction(self):
        """Tapo_P100_ABC -> model='P100'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.metadata["model"] == "P100"

    # --- local_name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to the raw local_name."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "Tapo_P100_ABC"

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac:tplink_tapo)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:tplink_tapo".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex_with_manufacturer_data(self):
        """raw_payload_hex is hex of manufacturer payload if present."""
        parser = TpLinkTapoParser()
        mfr_data = b"\x01\x02\xDE\xAD\xBE\xEF"
        ad = _make_ad(local_name="Tapo_P100_ABC", manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr_data.hex()

    def test_raw_payload_hex_empty_without_manufacturer_data(self):
        """raw_payload_hex is '' when no manufacturer_data."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    # --- Edge cases ---

    def test_returns_none_for_none_local_name(self):
        """Returns None when local_name is None."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name=None)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_non_matching_name(self):
        """Returns None for local_name that doesn't match."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_works_without_manufacturer_data(self):
        """Returns valid result with no manufacturer_data."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="Tapo_P100_ABC")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "tplink_tapo"
        assert result.raw_payload_hex == ""

    def test_case_insensitive_tapo(self):
        """Case insensitive: 'tapo_P100' matches, product_line='Tapo'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="tapo_P100")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["product_line"] == "Tapo"

    def test_case_insensitive_kasa(self):
        """Case insensitive: 'KASA_kp115' matches, product_line='Kasa'."""
        parser = TpLinkTapoParser()
        ad = _make_ad(local_name="KASA_kp115")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["product_line"] == "Kasa"
