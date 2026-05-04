"""Tests for Nespresso coffee machine plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.nespresso import NespressoParser


@pytest.fixture
def parser():
    return NespressoParser()


def make_raw(manufacturer_data=None, service_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


NESPRESSO_MFR_DATA = bytes.fromhex("0225408900000000")
NESPRESSO_PAYLOAD = bytes.fromhex("408900000000")
NESPRESSO_UUID = "06aa1910-f22a-11e3-9daa-0002a5d5c51b"


class TestNespressoParsing:
    def test_parse_valid_data(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result.parser_name == "nespresso"

    def test_beacon_type(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result.beacon_type == "nespresso"

    def test_device_class(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_identity_hash_format(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("nespresso:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_model_vertuo(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "Vertuo"
        assert result.metadata["model_code"] == "CV6"

    def test_model_venus(self, parser):
        raw = make_raw(
            manufacturer_data=bytes.fromhex("0225008900000000"),
            service_uuids=[NESPRESSO_UUID],
            local_name="Venus_D8132A9D825A",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "Venus"

    def test_mac_from_name(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result.metadata["device_mac"] == "FCB46765786E"

    def test_machine_state_byte(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
            local_name="Vertuo_CV6_FCB46765786E",
        )
        result = parser.parse(raw)
        assert result.metadata["state_byte"] == 0x40

    def test_machine_state_standby(self, parser):
        raw = make_raw(
            manufacturer_data=bytes.fromhex("0225008900000000"),
            service_uuids=[NESPRESSO_UUID],
            local_name="Venus_D8132A9D825A",
        )
        result = parser.parse(raw)
        assert result.metadata["state_byte"] == 0x00

    def test_parse_by_service_uuid_only(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
        )
        result = parser.parse(raw)
        assert result is not None

    def test_no_local_name(self, parser):
        raw = make_raw(
            manufacturer_data=NESPRESSO_MFR_DATA,
            service_uuids=[NESPRESSO_UUID],
        )
        result = parser.parse(raw)
        assert "model" not in result.metadata


class TestNespressoMalformed:
    """v1.1.0: UUID-only matches now succeed (per nespresso-activities report)."""

    def test_uuid_only_no_mfr_data_now_succeeds(self, parser):
        # Was: returns None. Per the report, the app filters on UUID alone
        # and doesn't parse mfr-data — UUID match is the canonical signal.
        raw = make_raw(service_uuids=[NESPRESSO_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["product_class"] == "coffee_machine"

    def test_returns_none_unrelated(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c00408900000000"))
        assert parser.parse(raw) is None


class TestNespressoAeroccino:
    """v1.1.0: Aeroccino milk frother detection."""

    def test_aeroccino_uuid(self, parser):
        from adwatch.plugins.nespresso import AEROCCINO_SERVICE_UUID
        raw = make_raw(service_uuids=[AEROCCINO_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["product_class"] == "aeroccino"

    def test_machine_uuid_classified_as_machine(self, parser):
        raw = make_raw(service_uuids=[NESPRESSO_UUID])
        result = parser.parse(raw)
        assert result.metadata["product_class"] == "coffee_machine"


class TestNespressoPluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Nespresso"
