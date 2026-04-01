"""Tests for Amazon Fire TV BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.amazon_fire_tv import AmazonFireTVParser


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
        name="amazon_fire_tv",
        service_uuid="fe00",
        local_name_pattern=r"^Fire TV",
        description="Amazon Fire TV streaming device advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(AmazonFireTVParser):
        pass

    return registry


def _fire_tv_service_data(header=0x01, padding=b"\x00" * 12, device_type_code=b"AFTM", extra=b""):
    """Build service data for fe00: header + padding + device_type_code + extra."""
    return bytes([header]) + padding + device_type_code + extra


class TestAmazonFireTVParser:
    def test_matches_service_uuid(self):
        """Matches on service_uuid fe00."""
        registry = _make_registry()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data()},
            local_name="Fire TV Stick",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name starting with 'Fire TV'."""
        registry = _make_registry()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data()},
            local_name="Fire TV Cube",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_parse_basic(self):
        """Parses valid Fire TV advertisement."""
        parser = AmazonFireTVParser()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data(header=0x02, device_type_code=b"AFTS")},
            local_name="Fire TV Stick",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "amazon_fire_tv"
        assert result.beacon_type == "amazon_fire_tv"
        assert result.device_class == "streaming_device"

    def test_header_in_metadata(self):
        """Header byte is extracted into metadata."""
        parser = AmazonFireTVParser()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data(header=0x42)},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["header"] == 0x42

    def test_device_type_code_in_metadata(self):
        """Device type code (bytes 13-16) is extracted into metadata."""
        parser = AmazonFireTVParser()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data(device_type_code=b"AFTM")},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_type_code"] == "AFTM"

    def test_device_name_in_metadata_when_local_name_present(self):
        """device_name is included in metadata when local_name is set."""
        parser = AmazonFireTVParser()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data()},
            local_name="Fire TV Stick 4K",
        )
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "Fire TV Stick 4K"

    def test_no_device_name_when_no_local_name(self):
        """device_name is not in metadata when local_name is None."""
        parser = AmazonFireTVParser()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data()},
        )
        result = parser.parse(ad)
        assert result is not None
        assert "device_name" not in result.metadata

    def test_identity_hash_format(self):
        """Identity hash is SHA256('amazon_fire_tv:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = AmazonFireTVParser()
        ad = _make_ad(
            service_data={"fe00": _fire_tv_service_data()},
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"amazon_fire_tv:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex contains full service data as hex."""
        parser = AmazonFireTVParser()
        data = _fire_tv_service_data(header=0xAB, device_type_code=b"CUBE")
        ad = _make_ad(service_data={"fe00": data})
        result = parser.parse(ad)
        assert result.raw_payload_hex == data.hex()

    def test_returns_none_for_no_service_data(self):
        """Returns None when service_data is None."""
        parser = AmazonFireTVParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_missing_fe00_key(self):
        """Returns None when service_data has no 'fe00' key."""
        parser = AmazonFireTVParser()
        ad = _make_ad(service_data={"fe01": b"\x00" * 20})
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_short_data(self):
        """Returns None when service data is less than 17 bytes."""
        parser = AmazonFireTVParser()
        ad = _make_ad(service_data={"fe00": b"\x00" * 16})
        result = parser.parse(ad)
        assert result is None

    def test_exactly_17_bytes_succeeds(self):
        """17 bytes is the minimum valid length."""
        parser = AmazonFireTVParser()
        data = b"\x01" + b"\x00" * 12 + b"AFTM"  # exactly 17 bytes
        ad = _make_ad(service_data={"fe00": data})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_type_code"] == "AFTM"

    def test_hex_string_service_data(self):
        """Handles service data provided as a hex string."""
        parser = AmazonFireTVParser()
        data = _fire_tv_service_data(device_type_code=b"AFTS")
        ad = _make_ad(service_data={"fe00": data.hex()})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_type_code"] == "AFTS"

    def test_non_ascii_device_type_code(self):
        """Non-ASCII bytes in device_type_code are replaced."""
        parser = AmazonFireTVParser()
        data = b"\x01" + b"\x00" * 12 + b"\xff\xfe\xfd\xfc"
        ad = _make_ad(service_data={"fe00": data})
        result = parser.parse(ad)
        assert result is not None
        # errors="replace" produces replacement characters
        assert len(result.metadata["device_type_code"]) == 4

    def test_longer_data_still_parses(self):
        """Data longer than 17 bytes is valid — extra bytes are ignored."""
        parser = AmazonFireTVParser()
        data = _fire_tv_service_data(device_type_code=b"AFTM", extra=b"\xDE\xAD\xBE\xEF")
        ad = _make_ad(service_data={"fe00": data})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_type_code"] == "AFTM"
        assert result.raw_payload_hex == data.hex()
