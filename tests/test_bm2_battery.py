"""Tests for BM2 car battery monitor plugin."""

import hashlib
import struct

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.bm2_battery import BM2BatteryParser

# Static AES key/IV from protocol spec
BM2_KEY = b'leagend\xff\xfe188246\x00'
BM2_IV = b'\x00' * 16


def _encrypt(plaintext: bytes) -> bytes:
    """Encrypt 16-byte plaintext with BM2 static key."""
    cipher = Cipher(algorithms.AES(BM2_KEY), modes.CBC(BM2_IV))
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()


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


def _voltage_payload(voltage: float) -> bytes:
    """Build a 16-byte plaintext for a given voltage."""
    # voltage = (raw >> 4) / 100.0  →  raw = int(voltage * 100) << 4
    raw = int(voltage * 100) << 4
    plaintext = b'\x01' + struct.pack(">H", raw) + b'\x00' * 13
    return plaintext


class TestBM2BatteryParser:
    def test_match_by_local_name_battery_monitor(self):
        """Should match local_name 'Battery Monitor'."""
        registry = ParserRegistry()

        @register_parser(
            name="bm2_battery", local_name_pattern=r"^(Battery Monitor|ZX-1689)$",
            service_uuid="fff0", description="BM2", version="1.0.0",
            core=False, registry=registry,
        )
        class TestParser(BM2BatteryParser):
            pass

        ad = _make_ad(local_name="Battery Monitor", service_uuids=["fff0"])
        assert len(registry.match(ad)) == 1

    def test_match_by_local_name_zx1689(self):
        """Should match local_name 'ZX-1689'."""
        registry = ParserRegistry()

        @register_parser(
            name="bm2_battery", local_name_pattern=r"^(Battery Monitor|ZX-1689)$",
            service_uuid="fff0", description="BM2", version="1.0.0",
            core=False, registry=registry,
        )
        class TestParser(BM2BatteryParser):
            pass

        ad = _make_ad(local_name="ZX-1689", service_uuids=["fff0"])
        assert len(registry.match(ad)) == 1

    def test_match_by_service_uuid(self):
        """Should match by service_uuid fff0."""
        registry = ParserRegistry()

        @register_parser(
            name="bm2_battery", local_name_pattern=r"^(Battery Monitor|ZX-1689)$",
            service_uuid="fff0", description="BM2", version="1.0.0",
            core=False, registry=registry,
        )
        class TestParser(BM2BatteryParser):
            pass

        ad = _make_ad(service_uuids=["fff0"])
        assert len(registry.match(ad)) == 1

    def test_successful_decryption_and_voltage(self):
        """Should decrypt and calculate voltage correctly."""
        plaintext = _voltage_payload(12.32)
        encrypted = _encrypt(plaintext)

        ad = _make_ad(
            manufacturer_data=encrypted,
            local_name="Battery Monitor",
            service_uuids=["fff0"],
        )
        parser = BM2BatteryParser()
        result = parser.parse(ad)

        assert result is not None
        assert result.parser_name == "bm2_battery"
        assert result.beacon_type == "bm2_battery"
        assert result.device_class == "sensor"
        assert result.metadata["voltage"] == pytest.approx(12.32, abs=0.01)
        assert result.metadata["encrypted"] is True

    def test_voltage_low_battery(self):
        """Should handle low voltage (11.5V)."""
        plaintext = _voltage_payload(11.50)
        encrypted = _encrypt(plaintext)

        ad = _make_ad(manufacturer_data=encrypted, local_name="Battery Monitor")
        parser = BM2BatteryParser()
        result = parser.parse(ad)

        assert result is not None
        assert result.metadata["voltage"] == pytest.approx(11.50, abs=0.01)

    def test_voltage_charging(self):
        """Should handle charging voltage (14.4V)."""
        plaintext = _voltage_payload(14.40)
        encrypted = _encrypt(plaintext)

        ad = _make_ad(manufacturer_data=encrypted, local_name="Battery Monitor")
        parser = BM2BatteryParser()
        result = parser.parse(ad)

        assert result is not None
        assert result.metadata["voltage"] == pytest.approx(14.40, abs=0.01)

    def test_too_short_data_returns_none(self):
        """Should return None if manufacturer_data is too short (< 16 bytes)."""
        ad = _make_ad(manufacturer_data=b'\x01\x02\x03', local_name="Battery Monitor")
        parser = BM2BatteryParser()
        result = parser.parse(ad)
        assert result is None

    def test_no_manufacturer_data_returns_none(self):
        """Should return None if no manufacturer_data."""
        ad = _make_ad(local_name="Battery Monitor")
        parser = BM2BatteryParser()
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:bm2_battery')[:16]."""
        plaintext = _voltage_payload(12.50)
        encrypted = _encrypt(plaintext)

        ad = _make_ad(
            manufacturer_data=encrypted,
            mac_address="11:22:33:44:55:66",
            local_name="Battery Monitor",
        )
        parser = BM2BatteryParser()
        result = parser.parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:bm2_battery".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_name_from_local_name(self):
        """device_name in metadata should come from local_name."""
        plaintext = _voltage_payload(12.80)
        encrypted = _encrypt(plaintext)

        ad = _make_ad(
            manufacturer_data=encrypted,
            local_name="Battery Monitor",
        )
        parser = BM2BatteryParser()
        result = parser.parse(ad)

        assert result.metadata.get("device_name") == "Battery Monitor"

    def test_raw_payload_hex(self):
        """raw_payload_hex should be the hex of the encrypted manufacturer_data."""
        plaintext = _voltage_payload(12.00)
        encrypted = _encrypt(plaintext)

        ad = _make_ad(manufacturer_data=encrypted, local_name="Battery Monitor")
        parser = BM2BatteryParser()
        result = parser.parse(ad)

        assert result.raw_payload_hex == encrypted.hex()
