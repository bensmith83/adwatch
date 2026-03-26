"""Tests for Fitbit fitness tracker BLE plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.fitbit import FitbitParser, QUALCOMM_COMPANY_ID, KNOWN_OPCODES


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
        name="fitbit",
        company_id=QUALCOMM_COMPANY_ID,
        local_name_pattern=r"(?i)^(Fitbit|Charge|Versa|Sense|Inspire|Luxe|Ace)",
        description="Fitbit fitness trackers",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(FitbitParser):
        pass

    return registry


class TestFitbitParser:
    def test_matches_company_id_with_known_opcode(self):
        """Matches company_id 0x000A with known opcode 0x01, parses airlink_opcode and device_type."""
        registry = _make_registry()
        # company_id 0x000A LE + opcode 0x01 + device_type 0x05
        mfr_data = struct.pack("<H", 0x000A) + bytes([0x01, 0x05])
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["airlink_opcode"] == 0x01
        assert result.metadata["airlink_state"] == "advertisement"
        assert result.metadata["device_type"] == 0x05

    def test_matches_local_name_fitbit(self):
        """Matches local name 'Fitbit Charge 5'."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x000A) + bytes([0x06, 0x03])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Fitbit Charge 5")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["device_name"] == "Fitbit Charge 5"
        assert result.metadata["airlink_state"] == "status"

    def test_rejects_unknown_opcode_without_fitbit_name(self):
        """Rejects company_id 0x000A with unknown opcode and no Fitbit name."""
        registry = _make_registry()
        # opcode 0xFF is not in KNOWN_OPCODES
        mfr_data = struct.pack("<H", 0x000A) + bytes([0xFF, 0x01])
        ad = _make_ad(manufacturer_data=mfr_data)
        matches = registry.match(ad)
        if matches:
            result = matches[0].parse(ad)
            assert result is None

    def test_presence_only_with_fitbit_name_no_mfr_data(self):
        """Returns presence_only when Fitbit name but no manufacturer data."""
        registry = _make_registry()
        ad = _make_ad(local_name="Charge 6")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["device_name"] == "Charge 6"
        assert result.raw_payload_hex == ""

    def test_device_class_is_wearable(self):
        """device_class is 'wearable'."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x000A) + bytes([0x01, 0x02])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Versa 4")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "wearable"

    def test_returns_none_when_no_fitbit_signal(self):
        """Returns None when no Fitbit signal at all."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x9999) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data)
        matches = registry.match(ad)
        if matches:
            result = matches[0].parse(ad)
            assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:fitbit')[:16]."""
        registry = _make_registry()
        mfr_data = struct.pack("<H", 0x000A) + bytes([0x01, 0x02])
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:fitbit".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected
