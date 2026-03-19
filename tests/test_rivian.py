"""Tests for Rivian Phone Key plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.rivian import RivianParser, RIVIAN_COMPANY_ID, RIVIAN_SERVICE_UUID


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


def _build_rivian_mfr_data(payload=b"\x01\x01\x06\x1a\x03\x63"):
    """Build Rivian mfr data: company_id(2) + payload."""
    return struct.pack("<H", RIVIAN_COMPANY_ID) + payload


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="rivian",
        company_id=RIVIAN_COMPANY_ID,
        service_uuid=RIVIAN_SERVICE_UUID,
        local_name_pattern=r"^Rivian Phone Key",
        description="Rivian Phone Key",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(RivianParser):
        pass

    return registry


class TestRivianParser:
    def test_match_company_id(self):
        """Should match company_id 0x0941 (Rivian)."""
        registry = _make_registry()
        mfr_data = _build_rivian_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid(self):
        """Should match by Rivian custom service UUID."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=[RIVIAN_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_local_name(self):
        """Should match by local name 'Rivian Phone Key'."""
        registry = _make_registry()
        ad = _make_ad(local_name="Rivian Phone Key")
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated(self):
        """Should not match unrelated advertisements."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=struct.pack("<H", 0x004C) + b"\x00",
            local_name="iPhone",
        )
        assert len(registry.match(ad)) == 0

    def test_parse_with_mfr_data(self):
        """Should parse advertisement with manufacturer data."""
        parser = RivianParser()
        mfr_data = _build_rivian_mfr_data()
        ad = _make_ad(
            manufacturer_data=mfr_data,
            local_name="Rivian Phone Key",
            service_uuids=[RIVIAN_SERVICE_UUID],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "rivian"
        assert result.beacon_type == "rivian_phone_key"
        assert result.device_class == "vehicle_key"
        assert result.metadata["device_name"] == "Rivian Phone Key"
        assert result.metadata["payload_len"] == 6

    def test_parse_uuid_only(self):
        """Should parse with service UUID only (no mfr data)."""
        parser = RivianParser()
        ad = _make_ad(
            service_uuids=[RIVIAN_SERVICE_UUID],
            local_name="Rivian Phone Key",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.beacon_type == "rivian_phone_key"

    def test_parse_name_only(self):
        """Should parse with local name only."""
        parser = RivianParser()
        ad = _make_ad(local_name="Rivian Phone Key")
        result = parser.parse(ad)
        assert result is not None
        assert result.beacon_type == "rivian_phone_key"

    def test_parse_returns_none_for_unrelated(self):
        """Should return None for unrelated advertisements."""
        parser = RivianParser()
        ad = _make_ad(
            manufacturer_data=struct.pack("<H", 0x004C) + b"\x00",
            local_name="iPhone",
        )
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:{local_name}')[:16]."""
        parser = RivianParser()
        mfr_data = _build_rivian_mfr_data()
        ad = _make_ad(
            manufacturer_data=mfr_data,
            mac_address="11:22:33:44:55:66",
            local_name="Rivian Phone Key",
            service_uuids=[RIVIAN_SERVICE_UUID],
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(
            "11:22:33:44:55:66:Rivian Phone Key".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """Raw payload hex should contain manufacturer payload."""
        parser = RivianParser()
        payload = b"\x01\x01\x06\x1a\x03\x63"
        mfr_data = _build_rivian_mfr_data(payload)
        ad = _make_ad(
            manufacturer_data=mfr_data,
            service_uuids=[RIVIAN_SERVICE_UUID],
            local_name="Rivian Phone Key",
        )
        result = parser.parse(ad)
        assert result.raw_payload_hex == payload.hex()

    def test_case_insensitive_uuid_match(self):
        """Should match uppercase UUIDs from some BLE stacks."""
        parser = RivianParser()
        ad = _make_ad(
            service_uuids=[RIVIAN_SERVICE_UUID.upper()],
            local_name="Rivian Phone Key",
        )
        result = parser.parse(ad)
        assert result is not None
