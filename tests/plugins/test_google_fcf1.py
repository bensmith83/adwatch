"""Tests for Google FCF1 cross-device beacon plugin."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.google_fcf1 import GoogleFcf1Parser


SAMPLE_PAYLOAD = bytes.fromhex(
    "045df48ae9ed11560478e73f8c3fe9cb28343026a47a"
)


@pytest.fixture
def parser():
    return GoogleFcf1Parser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-15T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=None,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=None,
        **defaults,
    )


class TestGoogleFcf1Parsing:
    def test_parses_sample_frame(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        assert parser.parse(raw).parser_name == "google_fcf1"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        assert parser.parse(raw).beacon_type == "google_fcf1"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        assert parser.parse(raw).device_class == "phone"

    def test_extracts_frame_type(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 4

    def test_extracts_payload_length(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == 22

    def test_records_payload_hex(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == SAMPLE_PAYLOAD.hex()

    def test_identifier_hash_format(self, parser):
        raw = make_raw(service_data={"fcf1": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestGoogleFcf1NonMatching:
    def test_returns_none_when_service_data_missing(self, parser):
        raw = make_raw(service_uuids=["fcf1"])
        assert parser.parse(raw) is None

    def test_returns_none_when_payload_empty(self, parser):
        raw = make_raw(service_data={"fcf1": b""})
        assert parser.parse(raw) is None

    def test_returns_none_for_other_service_uuid(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        assert parser.parse(raw) is None
