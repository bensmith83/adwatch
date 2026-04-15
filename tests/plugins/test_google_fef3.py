"""Tests for Google FEF3 cross-device companion plugin."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.google_fef3 import GoogleFef3Parser


SAMPLE_PAYLOAD = bytes.fromhex(
    "4a17234e38484e1132856c7db5ee6943c64d4bba81d84efed4ac8f"
)


@pytest.fixture
def parser():
    return GoogleFef3Parser()


def make_raw(service_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-15T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=None,
        service_data=service_data,
        service_uuids=[],
        local_name=None,
        **defaults,
    )


class TestGoogleFef3Parsing:
    def test_parses_sample_frame(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        assert parser.parse(raw).parser_name == "google_fef3"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        assert parser.parse(raw).beacon_type == "google_fef3"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        assert parser.parse(raw).device_class == "phone"

    def test_payload_length(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == 27

    def test_records_payload_hex(self, parser):
        raw = make_raw(service_data={"fef3": SAMPLE_PAYLOAD})
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == SAMPLE_PAYLOAD.hex()


class TestGoogleFef3NonMatching:
    def test_returns_none_when_payload_empty(self, parser):
        raw = make_raw(service_data={"fef3": b""})
        assert parser.parse(raw) is None

    def test_returns_none_when_no_service_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None
