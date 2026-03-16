"""Tests for Jaalee BLE sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser


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


def _build_service_data(temp_raw, humidity_raw, battery):
    """Build 5-byte service data: temp(int16 LE) + humidity(uint16 LE) + battery(uint8)."""
    return struct.pack("<hHB", temp_raw, humidity_raw, battery)


class TestJaaleeParser:
    def _registry_and_parser(self):
        from adwatch.plugins.jaalee import JaaleeParser

        registry = ParserRegistry()

        @register_parser(
            name="jaalee",
            service_uuid="9717",
            description="Jaalee temperature/humidity sensor",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(JaaleeParser):
            pass

        return registry

    def test_match_by_service_uuid(self):
        """Should match advertisements with service UUID 9717."""
        registry = self._registry_and_parser()
        data = _build_service_data(2500, 5000, 80)
        ad = _make_ad(service_data={"9717": data})
        assert len(registry.match(ad)) == 1

    def test_normal_values(self):
        """Parse normal temperature, humidity, and battery."""
        registry = self._registry_and_parser()
        # temp=2500 -> 25.00C, humidity=5000 -> 50.00%, battery=80%
        data = _build_service_data(2500, 5000, 80)
        ad = _make_ad(service_data={"9717": data})
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "jaalee"
        assert result.beacon_type == "jaalee"
        assert result.device_class == "sensor"
        assert result.metadata["temperature"] == pytest.approx(25.00)
        assert result.metadata["humidity"] == pytest.approx(50.00)
        assert result.metadata["battery"] == 80

    def test_negative_temperature(self):
        """Negative temperature (int16 LE)."""
        registry = self._registry_and_parser()
        # temp=-550 -> -5.50C
        data = _build_service_data(-550, 9900, 100)
        ad = _make_ad(service_data={"9717": data})
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(-5.50)
        assert result.metadata["humidity"] == pytest.approx(99.00)
        assert result.metadata["battery"] == 100

    def test_zero_values(self):
        """Zero temperature, humidity, and battery."""
        registry = self._registry_and_parser()
        data = _build_service_data(0, 0, 0)
        ad = _make_ad(service_data={"9717": data})
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(0.0)
        assert result.metadata["humidity"] == pytest.approx(0.0)
        assert result.metadata["battery"] == 0

    def test_no_service_data(self):
        """No service data returns None."""
        from adwatch.plugins.jaalee import JaaleeParser

        parser = JaaleeParser()
        ad = _make_ad(service_data=None)
        assert parser.parse(ad) is None

    def test_missing_uuid_key(self):
        """Service data without 9717 key returns None."""
        from adwatch.plugins.jaalee import JaaleeParser

        parser = JaaleeParser()
        ad = _make_ad(service_data={"abcd": b"\x00" * 5})
        assert parser.parse(ad) is None

    def test_too_short_data(self):
        """Service data shorter than 5 bytes returns None."""
        from adwatch.plugins.jaalee import JaaleeParser

        parser = JaaleeParser()
        ad = _make_ad(service_data={"9717": b"\x00\x01\x02\x03"})
        assert parser.parse(ad) is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:jaalee')[:16]."""
        registry = self._registry_and_parser()
        data = _build_service_data(2000, 5000, 50)
        ad = _make_ad(service_data={"9717": data}, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:jaalee".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex should be the hex of the service data bytes."""
        registry = self._registry_and_parser()
        data = _build_service_data(2500, 5000, 80)
        ad = _make_ad(service_data={"9717": data})
        result = registry.match(ad)[0].parse(ad)

        assert result.raw_payload_hex == data.hex()

    def test_exactly_5_bytes(self):
        """Exactly 5 bytes should parse successfully."""
        from adwatch.plugins.jaalee import JaaleeParser

        parser = JaaleeParser()
        data = _build_service_data(1000, 3000, 55)
        ad = _make_ad(service_data={"9717": data})
        result = parser.parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(10.00)
        assert result.metadata["humidity"] == pytest.approx(30.00)
        assert result.metadata["battery"] == 55
