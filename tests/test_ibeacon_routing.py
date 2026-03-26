"""Tests for iBeacon routing — company_id byte order matching."""

import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.parsers.ibeacon import IBeaconParser


def _make_ibeacon_data(company_id_bytes: bytes) -> bytes:
    """Build a valid iBeacon manufacturer_data payload with given company_id prefix."""
    subtype = b"\x02"
    length = b"\x15"
    uuid = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
    major = struct.pack(">H", 1)
    minor = struct.pack(">H", 2)
    tx_power = struct.pack("b", -59)
    return company_id_bytes + subtype + length + uuid + major + minor + tx_power


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="ibeacon",
        company_id=[0x004C, 0x4C00],
        description="Apple iBeacon",
        version="1.0",
        core=True,
        registry=registry,
    )
    class TestParser(IBeaconParser):
        pass

    return registry


def _make_raw(manufacturer_data: bytes) -> RawAdvertisement:
    return RawAdvertisement(
        timestamp="2026-01-01T00:00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        rssi=-70,
        manufacturer_data=manufacturer_data,
        service_uuids=[],
        service_data={},
        local_name=None,
        tx_power=None,
    )


class TestIBeaconRouting:
    """Registry routes iBeacon ads regardless of company_id byte order."""

    def test_matches_big_endian_company_id(self):
        """Registry matches when manufacturer_data has BE company_id (0x00 0x4C)."""
        registry = _make_registry()
        data = _make_ibeacon_data(b"\x00\x4c")
        raw = _make_raw(data)
        matches = registry.match(raw)
        assert len(matches) > 0, "Registry should match BE company_id 0x004C"

    def test_matches_little_endian_company_id(self):
        """Registry matches when manufacturer_data has LE company_id (0x4C 0x00)."""
        registry = _make_registry()
        data = _make_ibeacon_data(b"\x4c\x00")
        raw = _make_raw(data)
        matches = registry.match(raw)
        assert len(matches) > 0, "Registry should match LE company_id 0x4C00"

    def test_parse_with_be_company_id_returns_result(self):
        """Full parse of iBeacon ad with BE company_id returns correct ParseResult."""
        data = _make_ibeacon_data(b"\x00\x4c")
        raw = _make_raw(data)
        parser = IBeaconParser()
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "ibeacon"
        assert result.metadata["major"] == 1
        assert result.metadata["minor"] == 2
        assert result.metadata["tx_power"] == -59

    def test_parse_with_le_company_id_returns_result(self):
        """Full parse of iBeacon ad with LE company_id returns correct ParseResult."""
        data = _make_ibeacon_data(b"\x4c\x00")
        raw = _make_raw(data)
        parser = IBeaconParser()
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "ibeacon"
        assert result.metadata["major"] == 1
        assert result.metadata["minor"] == 2

    def test_default_registration_uses_both_byte_orders(self):
        """The default ibeacon registration should use both company_id byte orders."""
        from adwatch.registry import _default_registry

        # Find the ibeacon parser entry
        entry = None
        for e in _default_registry._parsers:
            if e.get("name") == "ibeacon":
                entry = e
                break
        assert entry is not None, "ibeacon parser should be registered"
        cid = entry["company_id"]
        assert isinstance(cid, (list, tuple)), "company_id should be a list"
        assert 0x004C in cid, "Should include BE company_id 0x004C"
        assert 0x4C00 in cid, "Should include LE company_id 0x4C00"
