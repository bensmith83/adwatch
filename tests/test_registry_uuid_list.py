"""Tests for service_uuid list support in ParserRegistry.

The registry supports lists for company_id but currently does NOT
support lists for service_uuid. This test verifies that list support
works for service_uuid matching.
"""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry


class FakeParser:
    """Minimal parser for registry testing."""
    def parse(self, raw):
        return "matched"


def make_raw(service_uuids=None, service_data=None, manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


class TestServiceUUIDListSupport:
    def test_single_uuid_still_works(self):
        """String service_uuid should still match (existing behavior)."""
        reg = ParserRegistry()
        parser = FakeParser()
        reg.register(
            name="test",
            service_uuid="fe78",
            description="test",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        raw = make_raw(service_uuids=["fe78"])
        assert reg.match(raw) == [parser]

    def test_uuid_list_matches_first(self):
        """List of UUIDs should match when first UUID is in service_uuids."""
        reg = ParserRegistry()
        parser = FakeParser()
        reg.register(
            name="test",
            service_uuid=["fe78", "febe"],
            description="test",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        raw = make_raw(service_uuids=["fe78"])
        assert reg.match(raw) == [parser]

    def test_uuid_list_matches_second(self):
        """List of UUIDs should match when second UUID is in service_uuids."""
        reg = ParserRegistry()
        parser = FakeParser()
        reg.register(
            name="test",
            service_uuid=["fe78", "febe"],
            description="test",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        raw = make_raw(service_uuids=["febe"])
        assert reg.match(raw) == [parser]

    def test_uuid_list_no_match(self):
        """List of UUIDs should not match when no UUID is present."""
        reg = ParserRegistry()
        parser = FakeParser()
        reg.register(
            name="test",
            service_uuid=["fe78", "febe"],
            description="test",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        raw = make_raw(service_uuids=["abcd"])
        assert reg.match(raw) == []

    def test_uuid_list_matches_service_data_key(self):
        """List of UUIDs should match when a UUID is a key in service_data."""
        reg = ParserRegistry()
        parser = FakeParser()
        reg.register(
            name="test",
            service_uuid=["fe78", "febe"],
            description="test",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        raw = make_raw(service_data={"febe": b"\x01\x02"})
        assert reg.match(raw) == [parser]

    def test_uuid_list_no_match_service_data(self):
        """List of UUIDs should not match unrelated service_data keys."""
        reg = ParserRegistry()
        parser = FakeParser()
        reg.register(
            name="test",
            service_uuid=["fe78", "febe"],
            description="test",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        raw = make_raw(service_data={"abcd": b"\x01\x02"})
        assert reg.match(raw) == []
