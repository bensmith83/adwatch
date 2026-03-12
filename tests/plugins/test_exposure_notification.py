"""Tests for Exposure Notification (GAEN) BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig
from adwatch.plugins.exposure_notification import ExposureNotificationParser


@pytest.fixture
def parser():
    return ExposureNotificationParser()


SERVICE_UUID = "0000fd6f-0000-1000-8000-00805f9b34fb"

# 16-byte Rolling Proximity Identifier + 4-byte Associated Encrypted Metadata
SAMPLE_RPI = bytes(range(0x10, 0x20))  # 16 bytes
SAMPLE_AEM = bytes([0x40, 0xF4, 0x00, 0x00])  # version nibble, TX power -12, reserved
VALID_DATA = SAMPLE_RPI + SAMPLE_AEM  # 20 bytes total


def make_raw(service_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        local_name=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(service_data=service_data, **defaults)


class TestExposureNotificationParsing:
    def test_valid_20_byte_data(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_rpi_extraction(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.metadata["rpi_hex"] == SAMPLE_RPI.hex()

    def test_aem_extraction(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.metadata["aem_hex"] == SAMPLE_AEM.hex()

    def test_tx_power_parsing(self, parser):
        # AEM byte index 1 is TX power as signed int8
        # 0xF4 = -12 as signed
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.metadata["tx_power"] == -12

    def test_tx_power_positive(self, parser):
        aem = bytes([0x40, 0x04, 0x00, 0x00])  # TX power = +4
        data = SAMPLE_RPI + aem
        raw = make_raw(service_data={SERVICE_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["tx_power"] == 4

    def test_tx_power_zero(self, parser):
        aem = bytes([0x40, 0x00, 0x00, 0x00])
        data = SAMPLE_RPI + aem
        raw = make_raw(service_data={SERVICE_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["tx_power"] == 0


class TestExposureNotificationFields:
    def test_parser_name(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "exposure_notification"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "exposure_notification"

    def test_device_class(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.device_class == "phone"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == VALID_DATA.hex()


class TestExposureNotificationIdentity:
    def test_identity_hash_from_rpi(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        expected = hashlib.sha256(SAMPLE_RPI.hex().encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_different_rpi_different_hash(self, parser):
        rpi1 = bytes(range(0x10, 0x20))
        rpi2 = bytes(range(0x20, 0x30))
        aem = bytes([0x40, 0x00, 0x00, 0x00])
        raw1 = make_raw(service_data={SERVICE_UUID: rpi1 + aem})
        raw2 = make_raw(service_data={SERVICE_UUID: rpi2 + aem})
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestExposureNotificationRejectsInvalid:
    def test_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_missing_uuid_key(self, parser):
        raw = make_raw(service_data={"0000aaaa-0000-1000-8000-00805f9b34fb": b"\x00" * 20})
        assert parser.parse(raw) is None

    def test_empty_data(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: b""})
        assert parser.parse(raw) is None

    def test_too_short_data(self, parser):
        raw = make_raw(service_data={SERVICE_UUID: b"\x00" * 19})
        assert parser.parse(raw) is None

    def test_empty_service_data_dict(self, parser):
        raw = make_raw(service_data={})
        assert parser.parse(raw) is None


class TestExposureNotificationRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = ExposureNotificationParser()
        reg.register(
            name="exposure_notification",
            service_uuid=SERVICE_UUID,
            description="Exposure Notification (GAEN)",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(service_data={SERVICE_UUID: VALID_DATA})
        matched = reg.match(raw)
        assert any(isinstance(p, ExposureNotificationParser) for p in matched)

    def test_not_core(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = ExposureNotificationParser()
        reg.register(
            name="exposure_notification",
            service_uuid=SERVICE_UUID,
            description="Exposure Notification (GAEN)",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        info = reg.get_by_name("exposure_notification")
        assert info.core is False


class TestExposureNotificationUIConfig:
    def test_ui_config_returns_tab(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert isinstance(cfg, PluginUIConfig)
        assert cfg.tab_name == "Exposure Notification"

    def test_ui_config_has_data_table(self, parser):
        cfg = parser.ui_config()
        assert len(cfg.widgets) > 0
        assert cfg.widgets[0].widget_type == "data_table"

    def test_ui_config_has_render_hints(self, parser):
        cfg = parser.ui_config()
        hints = cfg.widgets[0].render_hints
        assert "columns" in hints
        assert isinstance(hints["columns"], list)

    def test_api_router_returns_router(self, parser):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        router = parser.api_router(mock_db)
        assert router is not None

    def test_api_router_none_without_db(self, parser):
        assert parser.api_router(None) is None
