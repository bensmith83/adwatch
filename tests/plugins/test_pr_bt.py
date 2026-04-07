"""Tests for PR BT (portable Bluetooth device) plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.pr_bt import PrBtParser


@pytest.fixture
def parser():
    return PrBtParser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-06T00:00:00+00:00",
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


PR_BT_UUID = "4553867f-f809-49f4-aefc-e190a1f459f3"


class TestPrBtParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_uuids=["180a", PR_BT_UUID], local_name="PR BT 06CD")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_uuids=["180a", PR_BT_UUID], local_name="PR BT 06CD")
        result = parser.parse(raw)
        assert result.parser_name == "pr_bt"

    def test_beacon_type(self, parser):
        raw = make_raw(service_uuids=["180a", PR_BT_UUID], local_name="PR BT 06CD")
        result = parser.parse(raw)
        assert result.beacon_type == "pr_bt"

    def test_device_class(self, parser):
        raw = make_raw(service_uuids=["180a", PR_BT_UUID], local_name="PR BT 06CD")
        result = parser.parse(raw)
        assert result.device_class == "peripheral"

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_uuids=["180a", PR_BT_UUID], local_name="PR BT 06CD")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_id(self, parser):
        raw = make_raw(service_uuids=["180a", PR_BT_UUID], local_name="PR BT 06CD")
        result = parser.parse(raw)
        assert result.metadata["device_id"] == "06CD"

    def test_match_by_name_only(self, parser):
        raw = make_raw(local_name="PR BT ABCD")
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_uuid_only(self, parser):
        raw = make_raw(service_uuids=[PR_BT_UUID])
        result = parser.parse(raw)
        assert result is not None


class TestPrBtMalformed:
    def test_returns_none_no_match(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_uuids=["abcd"])
        assert parser.parse(raw) is None
