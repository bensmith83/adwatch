"""Tests for Govee LED light strips and bulbs BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.govee_led import GoveeLedParser


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
        name="govee_led",
        local_name_pattern=r"^(?:Govee|GBK|ihoment)_H",
        description="Govee LED light strips and bulbs",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GoveeLedParser):
        pass

    return registry


class TestGoveeLedRegistry:
    def test_matches_govee_name(self):
        """Matches on local_name 'Govee_H618A_2846' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="Govee_H618A_2846")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_gbk_name(self):
        """Matches on local_name 'GBK_H6114_386D' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="GBK_H6114_386D")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_ihoment_name(self):
        """Matches on local_name 'ihoment_H6110_8F62' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="ihoment_H6110_8F62")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestGoveeLedParser:
    def test_parser_name(self):
        """parser_name is 'govee_led'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="Govee_H618A_2846")
        result = parser.parse(ad)
        assert result.parser_name == "govee_led"

    def test_beacon_type(self):
        """beacon_type is 'govee_led'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="Govee_H618A_2846")
        result = parser.parse(ad)
        assert result.beacon_type == "govee_led"

    def test_device_class(self):
        """device_class is 'led_light'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="Govee_H618A_2846")
        result = parser.parse(ad)
        assert result.device_class == "led_light"

    def test_govee_model_and_device_id(self):
        """'Govee_H618A_2846' -> model='H618A', device_id='2846'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="Govee_H618A_2846")
        result = parser.parse(ad)
        assert result.metadata["model"] == "H618A"
        assert result.metadata["device_id"] == "2846"

    def test_gbk_model_and_device_id(self):
        """'GBK_H6114_386D' -> model='H6114', device_id='386D'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="GBK_H6114_386D")
        result = parser.parse(ad)
        assert result.metadata["model"] == "H6114"
        assert result.metadata["device_id"] == "386D"

    def test_ihoment_model_and_device_id(self):
        """'ihoment_H6110_8F62' -> model='H6110', device_id='8F62'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="ihoment_H6110_8F62")
        result = parser.parse(ad)
        assert result.metadata["model"] == "H6110"
        assert result.metadata["device_id"] == "8F62"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'Govee_H618A_2846'."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="Govee_H618A_2846")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Govee_H618A_2846"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:govee_led)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = GoveeLedParser()
        ad = _make_ad(local_name="Govee_H618A_2846", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:govee_led".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_sensor_company_id(self):
        """Returns None when company_id is 0xEC88 (sensor, not LED)."""
        parser = GoveeLedParser()
        mfr_data = (0xEC88).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(
            local_name="Govee_H618A_2846",
            manufacturer_data=mfr_data,
        )
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_non_govee_name(self):
        """Returns None for non-Govee name."""
        parser = GoveeLedParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_name(self):
        """Returns None when local_name is None."""
        parser = GoveeLedParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None
