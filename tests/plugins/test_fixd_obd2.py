"""Tests for FIXD OBD2 scanner plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.fixd_obd2 import FixdObd2Parser


@pytest.fixture
def parser():
    return FixdObd2Parser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-09T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


FIXD_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"


class TestFixdObd2Parsing:
    def test_parse_by_name(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_by_uuid_and_name(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=[FIXD_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert result.parser_name == "fixd_obd2"

    def test_beacon_type(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert result.beacon_type == "fixd_obd2"

    def test_device_class_automotive(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert result.device_class == "automotive"

    def test_identity_hash_format(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_value(self, parser):
        raw = make_raw(
            local_name="FIXD",
            service_uuids=["fff0"],
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_metadata_device_name(self, parser):
        raw = make_raw(local_name="FIXD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "FIXD"

    def test_no_match_wrong_name(self, parser):
        raw = make_raw(local_name="SomeOBD", service_uuids=["fff0"])
        result = parser.parse(raw)
        assert result is None

    def test_no_match_empty(self, parser):
        raw = make_raw()
        result = parser.parse(raw)
        assert result is None

    def test_matches_by_mac_prefix_without_name(self, parser):
        # Per passive report the FIXD app uses MAC-prefix matching — plain
        # Viecar/Seto OBD-II dongles with no "FIXD" name should still be
        # detected.
        raw = make_raw(mac_address="88:1B:99:AA:BB:CC")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["sensor_model"] == "VIECAR"

    def test_matches_setosmart_prefix(self, parser):
        raw = make_raw(mac_address="00:11:67:11:12:34")
        assert parser.parse(raw).metadata["sensor_model"] == "SETOSMART"

    def test_matches_viecar_v2_prefix(self, parser):
        raw = make_raw(mac_address="66:1B:11:AA:BB:CC")
        assert parser.parse(raw).metadata["sensor_model"] == "VIECAR_V2"

    def test_matches_old_kickstarter_exact_mac(self, parser):
        raw = make_raw(mac_address="00:0D:18:00:00:01")
        assert parser.parse(raw).metadata["sensor_model"] == "OLD_KICKSTARTER"

    def test_unrecognised_mac_without_name_does_not_match(self, parser):
        raw = make_raw(mac_address="AA:BB:CC:DD:EE:FF", service_uuids=["fff0"])
        assert parser.parse(raw) is None
