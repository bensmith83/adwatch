"""Tests for Matter commissioning plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.matter import MatterParser


@pytest.fixture
def parser():
    return MatterParser()


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


# Matter: opcode=0x01, discriminator=0x123, vendor=0x1001, product=0x0042, flags=0x00
MATTER_DATA = bytes([0x01, 0x23, 0x01, 0x01, 0x10, 0x42, 0x00, 0x00])


class TestMatterParsing:
    def test_parse_valid_matter(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "matter"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result.device_class == "smart_home"

    def test_extracts_discriminator(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result.metadata["discriminator"] == 0x123

    def test_extracts_vendor_id(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result.metadata["vendor_id"] == 0x1001

    def test_extracts_product_id(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result.metadata["product_id"] == 0x0042

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac:discriminator:vendor:product)[:16]."""
        raw = make_raw(
            service_data={"fff6": MATTER_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "AA:BB:CC:DD:EE:FF:123:1001:0042".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestMatterStorage:
    def test_storage_schema(self, parser):
        schema = parser.storage_schema()
        assert schema is not None
        assert "CREATE TABLE" in schema
        assert "matter_sightings" in schema

    def test_parse_produces_storage_row(self, parser):
        raw = make_raw(service_data={"fff6": MATTER_DATA})
        result = parser.parse(raw)
        assert result.storage_table == "matter_sightings"
        assert result.storage_row is not None
        assert result.storage_row["discriminator"] == 0x123


class TestMatterMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": MATTER_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_short_data(self, parser):
        raw = make_raw(service_data={"fff6": b"\x01\x23"})
        assert parser.parse(raw) is None

    def test_returns_none_wrong_opcode(self, parser):
        bad_data = bytes([0x02, 0x23, 0x01, 0x01, 0x10, 0x42, 0x00, 0x00])
        raw = make_raw(service_data={"fff6": bad_data})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(service_data={"fff6": b""})
        assert parser.parse(raw) is None
