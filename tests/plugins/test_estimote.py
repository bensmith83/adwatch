"""Tests for Estimote beacon plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.estimote import EstimoteParser


@pytest.fixture
def parser():
    return EstimoteParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-07T00:00:00+00:00",
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


ESTIMOTE_DATA = bytes.fromhex("0088faf71db7e8966183557677a402b304504440")


class TestEstimoteParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "estimote"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "estimote"

    def test_device_class_beacon(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.device_class == "beacon"

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac:service_data_hex)[:16]."""
        raw = make_raw(
            service_data={"fe9a": ESTIMOTE_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{ESTIMOTE_DATA.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == ESTIMOTE_DATA.hex()

    def test_metadata_payload_hex(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == ESTIMOTE_DATA.hex()

    def test_metadata_payload_length(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == len(ESTIMOTE_DATA)

    def test_metadata_protocol_version(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == 0

    def test_metadata_frame_type(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        # Byte 0 lower nibble = frame type
        assert result.metadata["frame_type"] == 0

    def test_metadata_frame_type_name(self, parser):
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.metadata["frame_type_name"] == "unknown"

    def test_metadata_short_identifier(self, parser):
        """Bytes 1-8 = short identifier as hex string."""
        raw = make_raw(service_data={"fe9a": ESTIMOTE_DATA})
        result = parser.parse(raw)
        assert result.metadata["short_identifier"] == "88faf71db7e89661"

    def test_telemetry_frame_type(self, parser):
        """Frame type 2 = telemetry."""
        data = bytearray(ESTIMOTE_DATA)
        data[0] = 0x22  # frame_type=2, protocol_version=2
        raw = make_raw(service_data={"fe9a": bytes(data)})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 2
        assert result.metadata["frame_type_name"] == "telemetry"
        assert result.metadata["protocol_version"] == 2

    def test_nearable_frame_type(self, parser):
        """Frame type 1 = nearable."""
        data = bytearray(ESTIMOTE_DATA)
        data[0] = 0x01  # frame_type=1, protocol_version=0
        raw = make_raw(service_data={"fe9a": bytes(data)})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 1
        assert result.metadata["frame_type_name"] == "nearable"

    def test_short_identifier_different_data(self, parser):
        """Different payload = different short identifier."""
        data = bytearray(20)
        data[0] = 0x02
        data[1:9] = b'\xde\xad\xbe\xef\xca\xfe\xba\xbe'
        raw = make_raw(service_data={"fe9a": bytes(data)})
        result = parser.parse(raw)
        assert result.metadata["short_identifier"] == "deadbeefcafebabe"

    def test_short_payload_no_identifier(self, parser):
        """Payload too short for identifier still parses basic fields."""
        data = bytes([0x20])  # 1 byte only
        raw = make_raw(service_data={"fe9a": data})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["frame_type"] == 0
        assert result.metadata["protocol_version"] == 2
        assert result.metadata["short_identifier"] is None

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Estimote"

    def test_has_api_router(self, parser):
        from unittest.mock import AsyncMock
        router = parser.api_router(db=AsyncMock())
        assert router is not None


class TestEstimoteMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": ESTIMOTE_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(service_data={"fe9a": b""})
        assert parser.parse(raw) is None
