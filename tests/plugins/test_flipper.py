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


# --- Enrichment from apk-ble-hunting flipperdevices-app report (2026-10-01) ---

SERIAL_UUID = "8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000"


class TestFlipperReportEnrichment:
    def _entry(self):
        import adwatch.plugins.flipper  # noqa: F401  (registers on import)
        from adwatch.registry import _default_registry
        entry = next(e for e in _default_registry._parsers if e["name"] == "flipper")
        return lambda raw: _default_registry._entry_matches(entry, raw)

    def test_serial_service_uuid_matches_parse(self, parser):
        raw = make_raw(service_uuids=[SERIAL_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["serial_service"] is True

    def test_oui_only_matches_parse(self, parser):
        raw = make_raw(mac_address="80:E1:26:12:34:56", address_type="public")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["flipper_oui"] is True

    def test_registry_matches_serial_uuid_and_oui(self):
        m = self._entry()
        assert m(make_raw(service_uuids=[SERIAL_UUID.upper()]))
        assert m(make_raw(mac_address="80:e1:26:aa:bb:cc"))
        assert not m(make_raw(mac_address="80:E1:27:aa:bb:cc"))

    def test_module_constants(self):
        import adwatch.plugins.flipper as mod
        assert SERIAL_UUID in mod.FLIPPER_SERVICE_UUIDS
        assert "3081" in mod.FLIPPER_SERVICE_UUIDS
        assert mod.FLIPPER_OUI == "80:E1:26"

    def test_flipper_name_suffix_extracted(self, parser):
        raw = make_raw(local_name="Flipper Zqx3")
        result = parser.parse(raw)
        assert result.metadata["flipper_name"] == "Zqx3"
        assert result.metadata["device_name"] == "Flipper Zqx3"

    def test_bare_flipper_name_no_suffix(self, parser):
        raw = make_raw(local_name="Flipper")
        result = parser.parse(raw)
        assert "flipper_name" not in result.metadata

    def test_non_oui_mac_flag_false(self, parser):
        raw = make_raw(local_name="Flipper Zqx3")
        assert parser.parse(raw).metadata["flipper_oui"] is False
