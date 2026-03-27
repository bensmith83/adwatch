"""Tests for Nordic Thingy:52 presence plugin."""
import pytest
from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser


THINGY_UUID = "ef680100-9b35-4933-9b10-52ffa9740042"

_reg = ParserRegistry()


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


# Import plugin with isolated registry
from adwatch.plugins.nordic_thingy import NordicThingyParser  # noqa: E402

_parser = NordicThingyParser()


class TestNordicThingyMatching:
    def test_matches_on_service_uuid_in_list(self):
        ad = _make_ad(service_uuids=[THINGY_UUID])
        result = _parser.parse(ad)
        assert result is not None
        assert result.parser_name == "nordic_thingy"

    def test_matches_on_local_name_thingy(self):
        ad = _make_ad(local_name="Thingy")
        result = _parser.parse(ad)
        assert result is not None
        assert result.parser_name == "nordic_thingy"

    def test_matches_on_local_name_thingy_custom(self):
        ad = _make_ad(local_name="Thingy:52-Bedroom")
        result = _parser.parse(ad)
        assert result is not None
        assert result.parser_name == "nordic_thingy"

    def test_returns_none_no_uuid_no_matching_name(self):
        ad = _make_ad(local_name="SomeOtherDevice")
        result = _parser.parse(ad)
        assert result is None

    def test_returns_none_no_data_at_all(self):
        ad = _make_ad()
        result = _parser.parse(ad)
        assert result is None


class TestNordicThingyDeviceId:
    def test_parses_random_device_id_from_nordic_mfr_data(self):
        # Company ID 0x0059 (LE) + 4 bytes device ID
        mfr_data = bytes([0x59, 0x00, 0xAA, 0xBB, 0xCC, 0xDD])
        ad = _make_ad(service_uuids=[THINGY_UUID], manufacturer_data=mfr_data)
        result = _parser.parse(ad)
        assert result is not None
        # Reversed byte order: DD CC BB AA
        assert result.metadata["random_device_id"] == "ddccbbaa"

    def test_no_device_id_when_manufacturer_data_missing(self):
        ad = _make_ad(service_uuids=[THINGY_UUID])
        result = _parser.parse(ad)
        assert result is not None
        assert "random_device_id" not in result.metadata

    def test_no_device_id_when_company_id_not_nordic(self):
        # Company ID 0x004C (Apple), not Nordic
        mfr_data = bytes([0x4C, 0x00, 0xAA, 0xBB, 0xCC, 0xDD])
        ad = _make_ad(service_uuids=[THINGY_UUID], manufacturer_data=mfr_data)
        result = _parser.parse(ad)
        assert result is not None
        assert "random_device_id" not in result.metadata


class TestNordicThingyMetadata:
    def test_returns_device_name_from_local_name(self):
        ad = _make_ad(local_name="Thingy:52-Bedroom", service_uuids=[THINGY_UUID])
        result = _parser.parse(ad)
        assert result.metadata["device_name"] == "Thingy:52-Bedroom"

    def test_device_class_is_dev_kit(self):
        ad = _make_ad(service_uuids=[THINGY_UUID])
        result = _parser.parse(ad)
        assert result is not None
        assert result.device_class == "dev_kit"

    def test_beacon_type_is_nordic_thingy(self):
        ad = _make_ad(service_uuids=[THINGY_UUID])
        result = _parser.parse(ad)
        assert result.beacon_type == "nordic_thingy"
