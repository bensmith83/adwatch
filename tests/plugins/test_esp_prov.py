"""Tests for ESP32 Wi-Fi Provisioning plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.esp_prov import EspProvParser, ESP_PROV_SERVICE_UUID


@pytest.fixture
def parser():
    return EspProvParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
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
        **defaults,
    )


class TestEspProvParsing:
    def test_parse_via_service_uuids(self, parser):
        raw = make_raw(service_uuids=[ESP_PROV_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_via_service_data(self, parser):
        raw = make_raw(service_data={ESP_PROV_SERVICE_UUID: b"\x01\x02"})
        result = parser.parse(raw)
        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=[ESP_PROV_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.parser_name == "esp_prov"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=[ESP_PROV_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.beacon_type == "esp_wifi_prov"

    def test_device_class(self, parser):
        raw = make_raw(service_uuids=[ESP_PROV_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.device_class == "iot"

    def test_captures_device_name(self, parser):
        raw = make_raw(
            service_uuids=[ESP_PROV_SERVICE_UUID],
            local_name="EKG_A1B2",
        )
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "EKG_A1B2"

    def test_identity_hash(self, parser):
        raw = make_raw(
            service_uuids=[ESP_PROV_SERVICE_UUID],
            mac_address="AA:BB:CC:DD:EE:FF",
            local_name="EKG_TEST",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "AA:BB:CC:DD:EE:FF:EKG_TEST".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=[ESP_PROV_SERVICE_UUID])
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_empty_name_handled(self, parser):
        raw = make_raw(service_uuids=[ESP_PROV_SERVICE_UUID], local_name=None)
        result = parser.parse(raw)
        assert result.metadata["device_name"] == ""

    def test_service_data_hex_captured(self, parser):
        raw = make_raw(service_data={ESP_PROV_SERVICE_UUID: b"\xaa\xbb\xcc"})
        result = parser.parse(raw)
        assert result.raw_payload_hex == "aabbcc"
        assert result.metadata["service_data_len"] == 3


class TestEspProvStorage:
    def test_storage_schema(self, parser):
        schema = parser.storage_schema()
        assert schema is not None
        assert "CREATE TABLE" in schema
        assert "esp_prov_sightings" in schema

    def test_parse_produces_storage_row(self, parser):
        raw = make_raw(
            service_uuids=[ESP_PROV_SERVICE_UUID],
            local_name="EKG_DEVICE",
        )
        result = parser.parse(raw)
        assert result.storage_table == "esp_prov_sightings"
        assert result.storage_row is not None
        assert result.storage_row["device_name"] == "EKG_DEVICE"
        assert result.storage_row["mac_address"] == "AA:BB:CC:DD:EE:FF"


class TestEspProvMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(service_data=None, service_uuids=[])
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["00001800-0000-1000-8000-00805f9b34fb"])
        assert parser.parse(raw) is None

    def test_returns_none_wrong_service_data_key(self, parser):
        raw = make_raw(service_data={"abcd": b"\x01\x02"})
        assert parser.parse(raw) is None
