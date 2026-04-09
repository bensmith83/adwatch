"""Tests for Google FE9F BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.google_fe9f import (
    GoogleFe9fParser,
    GOOGLE_FE9F_UUID,
)


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="google_fe9f",
        service_uuid=GOOGLE_FE9F_UUID,
        description="Google FE9F BLE service",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GoogleFe9fParser):
        pass

    return registry


def _fe9f_service_data(payload=b"\x00" * 20):
    """Build service data dict with FE9F UUID."""
    return {GOOGLE_FE9F_UUID: payload}


class TestGoogleFe9fParser:
    def test_matches_service_uuid(self):
        """Registry matches on service UUID fe9f."""
        registry = _make_registry()
        ad = _make_ad(service_data=_fe9f_service_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_parser_name(self):
        """parser_name is 'google_fe9f'."""
        parser = GoogleFe9fParser()
        ad = _make_ad(service_data=_fe9f_service_data())
        result = parser.parse(ad)
        assert result.parser_name == "google_fe9f"

    def test_beacon_type(self):
        """beacon_type is 'google_fe9f'."""
        parser = GoogleFe9fParser()
        ad = _make_ad(service_data=_fe9f_service_data())
        result = parser.parse(ad)
        assert result.beacon_type == "google_fe9f"

    def test_device_class(self):
        """device_class is 'phone'."""
        parser = GoogleFe9fParser()
        ad = _make_ad(service_data=_fe9f_service_data())
        result = parser.parse(ad)
        assert result.device_class == "phone"

    def test_identity_hash(self):
        """Identity hash is SHA256(google_fe9f:mac)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = GoogleFe9fParser()
        ad = _make_ad(service_data=_fe9f_service_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"google_fe9f:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_payload_hex_in_metadata(self):
        """payload_hex contains hex of service data."""
        parser = GoogleFe9fParser()
        payload = b"\xAB\xCD\xEF"
        ad = _make_ad(service_data=_fe9f_service_data(payload))
        result = parser.parse(ad)
        assert result.metadata["payload_hex"] == payload.hex()

    def test_payload_length_in_metadata(self):
        """payload_length is the byte count of service data."""
        parser = GoogleFe9fParser()
        payload = b"\x00" * 20
        ad = _make_ad(service_data=_fe9f_service_data(payload))
        result = parser.parse(ad)
        assert result.metadata["payload_length"] == 20

    def test_raw_payload_hex(self):
        """raw_payload_hex contains service data as hex."""
        parser = GoogleFe9fParser()
        payload = b"\xDE\xAD"
        ad = _make_ad(service_data=_fe9f_service_data(payload))
        result = parser.parse(ad)
        assert result.raw_payload_hex == payload.hex()

    def test_returns_none_no_service_data(self):
        """Returns None when service_data is None."""
        parser = GoogleFe9fParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_wrong_uuid(self):
        """Returns None when service data has different UUID."""
        parser = GoogleFe9fParser()
        ad = _make_ad(service_data={"fe2c": b"\x00" * 10})
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_empty_payload(self):
        """Returns None when service data payload is empty."""
        parser = GoogleFe9fParser()
        ad = _make_ad(service_data={GOOGLE_FE9F_UUID: b""})
        result = parser.parse(ad)
        assert result is None
