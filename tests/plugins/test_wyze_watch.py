"""Tests for Wyze Watch plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.wyze_watch import WyzeWatchParser


@pytest.fixture
def parser():
    return WyzeWatchParser()


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


WYZE_MFR_DATA = bytes.fromhex("4906020900002caa8ed26282")
WYZE_FE95_DATA = bytes.fromhex("31208f03002caa8ed2628209")


class TestWyzeWatchParsing:
    def test_parse_valid_data(self, parser):
        raw = make_raw(
            manufacturer_data=WYZE_MFR_DATA,
            service_data={"fe95": WYZE_FE95_DATA},
            service_uuids=["fe95", "b167", "fee7"],
            local_name="Wyze Watch 47",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(
            manufacturer_data=WYZE_MFR_DATA,
            local_name="Wyze Watch 47",
        )
        result = parser.parse(raw)
        assert result.parser_name == "wyze_watch"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert result.beacon_type == "wyze_watch"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert result.device_class == "wearable"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            manufacturer_data=WYZE_MFR_DATA,
            local_name="Wyze Watch 47",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("wyze_watch:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_watch_size_47(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert result.metadata["watch_size"] == "47"

    def test_watch_size_44(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 44")
        result = parser.parse(raw)
        assert result.metadata["watch_size"] == "44"

    def test_embedded_mac(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert result.metadata["embedded_mac"] == "2C:AA:8E:D2:62:82"

    def test_device_type_code(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "0209"

    def test_mibeacon_device_type(self, parser):
        raw = make_raw(
            manufacturer_data=WYZE_MFR_DATA,
            service_data={"fe95": WYZE_FE95_DATA},
            local_name="Wyze Watch 47",
        )
        result = parser.parse(raw)
        assert result.metadata["mibeacon_type"] == "8f03"

    def test_no_mibeacon_data(self, parser):
        raw = make_raw(manufacturer_data=WYZE_MFR_DATA, local_name="Wyze Watch 47")
        result = parser.parse(raw)
        assert "mibeacon_type" not in result.metadata

    def test_parse_by_name_only(self, parser):
        """Should match by local_name pattern even without expected company_id."""
        raw = make_raw(
            manufacturer_data=WYZE_MFR_DATA,
            local_name="Wyze Watch 47",
        )
        result = parser.parse(raw)
        assert result is not None


class TestWyzeWatchMalformed:
    def test_returns_none_wrong_name(self, parser):
        """Without matching name, needs non-Wyze company_id to reject."""
        raw = make_raw(manufacturer_data=bytes.fromhex("4c00020900002caa8ed26282"), local_name="Some Other Watch")
        assert parser.parse(raw) is None

    def test_returns_none_no_data_no_name(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_no_mfr_data_no_matching_name(self, parser):
        raw = make_raw(local_name="Not a Wyze")
        assert parser.parse(raw) is None


class TestWyzeWatchPluginMeta:
    def test_storage_schema_none(self, parser):
        assert parser.storage_schema() is None

    def test_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Wyze Watch"
