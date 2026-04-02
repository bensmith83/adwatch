"""Tests for Amazon Echo / Alexa BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.amazon_echo import AmazonEchoParser


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
        name="amazon_echo",
        local_name_pattern=r"^Echo\s",
        description="Amazon Echo / Alexa advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(AmazonEchoParser):
        pass

    return registry


class TestAmazonEchoRegistry:
    def test_matches_local_name_pattern(self):
        """Matches on local_name 'Echo Pop-35U' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="Echo Pop-35U")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestAmazonEchoParser:
    def test_parser_name(self):
        """parser_name is 'amazon_echo'."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Pop-35U")
        result = parser.parse(ad)
        assert result.parser_name == "amazon_echo"

    def test_beacon_type(self):
        """beacon_type is 'amazon_echo'."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Pop-35U")
        result = parser.parse(ad)
        assert result.beacon_type == "amazon_echo"

    def test_device_class(self):
        """device_class is 'smart_speaker'."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Pop-35U")
        result = parser.parse(ad)
        assert result.device_class == "smart_speaker"

    def test_model_echo_pop(self):
        """'Echo Pop-35U' -> metadata['model'] == 'Echo Pop'."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Pop-35U")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Echo Pop"

    def test_model_echo_dot(self):
        """'Echo Dot-XXX' -> metadata['model'] == 'Echo Dot'."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Dot-XXX")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Echo Dot"

    def test_device_name_in_metadata(self):
        """metadata['device_name'] == 'Echo Pop-35U'."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Pop-35U")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Echo Pop-35U"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:amazon_echo)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="Echo Pop-35U", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:amazon_echo".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_no_name(self):
        """Returns None when local_name is None."""
        parser = AmazonEchoParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_non_echo(self):
        """Returns None for non-Echo name."""
        parser = AmazonEchoParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None
