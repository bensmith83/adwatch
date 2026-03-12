"""Tests for ThermoPro plugin."""

import hashlib
import re

import pytest

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig
from adwatch.plugins.thermopro import ThermoProParser


@pytest.fixture
def parser():
    return ThermoProParser()


def make_raw(local_name=None, manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="11:22:33:44:55:66",
        address_type="random",
        service_data=None,
        service_uuids=[],
        rssi=-45,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        local_name=local_name,
        manufacturer_data=manufacturer_data,
        **defaults,
    )


# 21.5C, 55% humidity, TP357S model (0x0B)
TP357_MFGR_DATA = bytes([0xC2, 0xD7, 0x00, 0x37, 0x00, 0x0B, 0x01])

# -5.0C, 70% humidity, TP359S model (0x13)
TP359_MFGR_DATA = bytes([0xC2, 0xCE, 0xFF, 0x46, 0x00, 0x13, 0x01])


class TestThermoProParsing:
    def test_parse_tp357_returns_result(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.parser_name == "thermopro"

    def test_device_class_sensor(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_extracts_temperature(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(21.5)

    def test_extracts_humidity(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.metadata["humidity"] == 55

    def test_extracts_model_from_local_name(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "TP357"

    def test_negative_temperature(self, parser):
        raw = make_raw(
            local_name="TP359 (6708)",
            manufacturer_data=TP359_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-5.0)
        assert result.metadata["humidity"] == 70

    def test_identity_hash_from_local_name(self, parser):
        """Identity = SHA256('thermopro:{local_name}')[:16]."""
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "thermopro:TP357 (2B54)".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_different_local_names_different_hashes(self, parser):
        raw1 = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        raw2 = make_raw(
            local_name="TP357 (9999)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestThermoProVariousModels:
    def test_tp359_model(self, parser):
        raw = make_raw(
            local_name="TP359 (6708)",
            manufacturer_data=TP359_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "TP359"

    def test_tp351_model(self, parser):
        raw = make_raw(
            local_name="TP351 (0001)",
            manufacturer_data=bytes([0xC2, 0x00, 0x01, 0x32, 0x00, 0x33, 0x01]),
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "TP351"

    def test_model_with_suffix(self, parser):
        raw = make_raw(
            local_name="TP357S (3104)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "TP357S"


class TestThermoProMalformed:
    def test_returns_none_no_local_name(self, parser):
        raw = make_raw(
            local_name=None,
            manufacturer_data=TP357_MFGR_DATA,
        )
        assert parser.parse(raw) is None

    def test_returns_none_wrong_local_name(self, parser):
        raw = make_raw(
            local_name="SomeOtherDevice",
            manufacturer_data=TP357_MFGR_DATA,
        )
        assert parser.parse(raw) is None

    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=None,
        )
        assert parser.parse(raw) is None

    def test_returns_none_short_manufacturer_data(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=b"\xC2\xD7",
        )
        assert parser.parse(raw) is None


class TestThermoProStorageSchema:
    def test_returns_create_table(self, parser):
        schema = parser.storage_schema()
        assert schema is not None
        assert "CREATE TABLE" in schema
        assert "thermopro_sightings" in schema

    def test_schema_has_required_columns(self, parser):
        schema = parser.storage_schema()
        for col in ["timestamp", "mac_address", "temperature_c", "humidity",
                     "identifier_hash", "model_code"]:
            assert col in schema


class TestThermoProUIConfig:
    def test_returns_plugin_ui_config(self, parser):
        config = parser.ui_config()
        assert config is not None
        assert isinstance(config, PluginUIConfig)

    def test_tab_name(self, parser):
        config = parser.ui_config()
        assert config.tab_name == "ThermoPro"

    def test_has_sensor_card_widget(self, parser):
        config = parser.ui_config()
        widget_types = [w.widget_type for w in config.widgets]
        assert "sensor_card" in widget_types


class TestThermoProStorageRow:
    def test_parse_produces_storage_row(self, parser):
        raw = make_raw(
            local_name="TP357 (2B54)",
            manufacturer_data=TP357_MFGR_DATA,
        )
        result = parser.parse(raw)
        assert result.storage_table == "thermopro_sightings"
        assert result.storage_row is not None
        assert result.storage_row["temperature_c"] == pytest.approx(21.5)
        assert result.storage_row["humidity"] == 55
