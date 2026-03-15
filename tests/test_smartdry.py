"""Tests for SmartDry laundry sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.smartdry import SmartDryParser


COMPANY_ID = 0x01AE


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


def _build_mfr_data(temp_raw, humidity_raw, battery, shake):
    """Build manufacturer_data: company_id(LE) + temp(int16 LE) + humidity(uint16 LE) + battery(uint8) + shake(uint8)."""
    return struct.pack("<HhHBB", COMPANY_ID, temp_raw, humidity_raw, battery, shake)


class TestSmartDryParser:
    def _registry_and_parser(self):
        registry = ParserRegistry()

        @register_parser(
            name="smartdry",
            company_id=COMPANY_ID,
            description="SmartDry laundry sensor",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(SmartDryParser):
            pass

        return registry

    def test_match_by_company_id(self):
        """Should match advertisements with company_id 0x01AE."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(2500, 5000, 95, 128)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_normal_values(self):
        """Parse normal dryer running values."""
        registry = self._registry_and_parser()
        # temp=2500 -> 25.00C, humidity=5000 -> 50.00%, battery=95, shake=128
        mfr_data = _build_mfr_data(2500, 5000, 95, 128)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "smartdry"
        assert result.beacon_type == "smartdry"
        assert result.device_class == "sensor"
        assert result.metadata["temperature"] == pytest.approx(25.00)
        assert result.metadata["humidity"] == pytest.approx(50.00)
        assert result.metadata["battery"] == 95
        assert result.metadata["shake_intensity"] == 128

    def test_negative_temperature(self):
        """Negative temperature (int16 LE)."""
        registry = self._registry_and_parser()
        # temp=-550 -> -5.50C
        mfr_data = _build_mfr_data(-550, 8000, 100, 0)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(-5.50)
        assert result.metadata["humidity"] == pytest.approx(80.00)

    def test_zero_values(self):
        """All zeros — idle dryer."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0, 0, 0, 0)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(0.0)
        assert result.metadata["humidity"] == pytest.approx(0.0)
        assert result.metadata["battery"] == 0
        assert result.metadata["shake_intensity"] == 0

    def test_max_values(self):
        """Max shake intensity and high temp."""
        registry = self._registry_and_parser()
        # temp=7000 -> 70.00C, humidity=9999 -> 99.99%, battery=100, shake=255
        mfr_data = _build_mfr_data(7000, 9999, 100, 255)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(70.00)
        assert result.metadata["humidity"] == pytest.approx(99.99)
        assert result.metadata["battery"] == 100
        assert result.metadata["shake_intensity"] == 255

    def test_no_manufacturer_data(self):
        """No manufacturer data returns None."""
        parser = SmartDryParser()
        ad = _make_ad(manufacturer_data=None)
        result = parser.parse(ad)
        assert result is None

    def test_too_short_data(self):
        """Manufacturer data too short returns None."""
        parser = SmartDryParser()
        ad = _make_ad(manufacturer_data=b"\xae\x01\x00")
        result = parser.parse(ad)
        assert result is None

    def test_wrong_company_id(self):
        """Wrong company ID returns None."""
        parser = SmartDryParser()
        mfr_data = struct.pack("<HhHBB", 0xFFFF, 2500, 5000, 95, 128)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:smartdry')[:16]."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(2500, 5000, 95, 0)
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:smartdry".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex should be the hex of manufacturer_payload (without company ID)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(2500, 5000, 95, 128)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)

        # payload is bytes after company_id: temp(2) + humidity(2) + battery(1) + shake(1) = 6 bytes
        expected_payload = struct.pack("<hHBB", 2500, 5000, 95, 128)
        assert result.raw_payload_hex == expected_payload.hex()
