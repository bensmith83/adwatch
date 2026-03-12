"""Tests for Flipper Zero multi-tool plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.flipper import FlipperParser


@pytest.fixture
def parser():
    return FlipperParser()


def make_raw(service_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


FLIPPER_UUID = "00003081-0000-1000-8000-00805f9b34fb"


class TestFlipperParsing:
    def test_parse_valid_with_uuid_and_name(self, parser):
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_valid_name_only(self, parser):
        """Should parse with just local_name matching ^Flipper."""
        raw = make_raw(local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_valid_uuid_only(self, parser):
        """Should parse with just service UUID 3081."""
        raw = make_raw(service_uuids=[FLIPPER_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result.parser_name == "flipper"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result.beacon_type == "flipper"

    def test_device_class_tool(self, parser):
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result.device_class == "tool"

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac)[:16]."""
        raw = make_raw(
            service_uuids=[FLIPPER_UUID],
            local_name="Flipper Goldite",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(b"AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Flipper Goldite"

    def test_metadata_no_name(self, parser):
        """When no local_name, metadata should not have device_name."""
        raw = make_raw(service_uuids=[FLIPPER_UUID])
        result = parser.parse(raw)
        assert "device_name" not in result.metadata

    def test_raw_payload_hex_empty(self, parser):
        """No service data payload, so raw_payload_hex should be empty."""
        raw = make_raw(service_uuids=[FLIPPER_UUID], local_name="Flipper Goldite")
        result = parser.parse(raw)
        assert result.raw_payload_hex == ""

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Flipper"


class TestFlipperMalformed:
    def test_returns_none_no_match(self, parser):
        """Neither service UUID 3081 nor Flipper name present."""
        raw = make_raw(service_uuids=["0000abcd-0000-1000-8000-00805f9b34fb"], local_name="SomeDevice")
        assert parser.parse(raw) is None

    def test_returns_none_no_data_at_all(self, parser):
        """No service UUIDs or local name."""
        raw = make_raw()
        assert parser.parse(raw) is None
