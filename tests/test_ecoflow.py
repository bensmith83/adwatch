"""Tests for EcoFlow portable power station plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.ecoflow import EcoFlowParser, ECOFLOW_COMPANY_ID


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


def _build_full_payload(
    serial=b"R331ABCDEFGHIJKL",
    status=0x80,
    product_type=0x02,
    caps=0x47,
    protocol_version=1,
):
    """Build a full 23-byte EcoFlow manufacturer data payload (after company ID)."""
    # pad/truncate serial to 16 bytes
    serial = serial[:16].ljust(16, b"\x00")
    payload = bytes([protocol_version]) + serial + bytes([status, product_type])
    payload += b"\x00\x00\x00"  # reserved
    payload += bytes([caps])
    return payload


def _make_mfr_data(payload):
    """Prepend little-endian company ID to payload."""
    return struct.pack("<H", ECOFLOW_COMPANY_ID) + payload


class TestEcoFlowParser:
    def test_full_payload_parses(self):
        """Valid full payload parses serial, model, active, caps."""
        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        parser = EcoFlowParser()
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "ecoflow"
        assert result.beacon_type == "ecoflow"
        assert result.device_class == "power"
        assert result.metadata["serial_number"] == "R331ABCDEFGHIJKL"
        assert result.metadata["device_model"] == "DELTA 2"
        assert result.metadata["active"] is True
        assert result.metadata["product_type"] == 0x02
        assert result.metadata["protocol_version"] == 1

    def test_model_delta2_r331(self):
        """R331 prefix → DELTA 2."""
        payload = _build_full_payload(serial=b"R331XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "DELTA 2"

    def test_model_powerstream_hw51(self):
        """HW51 prefix → PowerStream."""
        payload = _build_full_payload(serial=b"HW51XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "PowerStream"

    def test_model_delta_mini_db(self):
        """DB prefix → DELTA mini."""
        payload = _build_full_payload(serial=b"DB12XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "DELTA mini"

    def test_model_delta_pro_3(self):
        """MR51 prefix → DELTA Pro 3."""
        payload = _build_full_payload(serial=b"MR51XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "DELTA Pro 3"

    def test_unknown_serial_prefix(self):
        """Unknown serial prefix returns 'Unknown EcoFlow'."""
        payload = _build_full_payload(serial=b"ZZ99XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "Unknown EcoFlow"

    def test_short_payload_parses_available(self):
        """Short payload (< 20 bytes) still parses what's available."""
        # Only protocol_version + serial (17 bytes)
        payload = bytes([0x02]) + b"R601ABCDEFGHIJKL"
        assert len(payload) == 17
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result is not None
        assert result.metadata["protocol_version"] == 2
        assert result.metadata["serial_number"] == "R601ABCDEFGHIJKL"
        assert result.metadata["device_model"] == "RIVER 2"
        # status/product_type should not be present
        assert "active" not in result.metadata
        assert "product_type" not in result.metadata

    def test_active_flag_bit7(self):
        """Active flag is bit 7 of status byte."""
        # status=0x80 → active=True
        payload = _build_full_payload(status=0x80)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["active"] is True

        # status=0x00 → active=False
        payload = _build_full_payload(status=0x00)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["active"] is False

        # status=0xFF → active=True (bit 7 set among others)
        payload = _build_full_payload(status=0xFF)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["active"] is True

    def test_capability_flags(self):
        """Capability flags are parsed correctly from byte 22."""
        # caps=0x47: encrypted(1), verification(1), verified(1), enc_type=0, 5ghz(1)
        # 0x47 = 0b01000111
        payload = _build_full_payload(caps=0x47)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["encrypted"] is True
        assert result.metadata["supports_verification"] is True
        assert result.metadata["verified"] is True
        assert result.metadata["encryption_type"] == 0
        assert result.metadata["supports_5ghz"] is True

    def test_capability_flags_encryption_type(self):
        """Encryption type extracted from bits 3-5."""
        # caps=0x28: enc_type=5 (0b101 << 3 = 0x28)
        payload = _build_full_payload(caps=0x28)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["encrypted"] is False
        assert result.metadata["encryption_type"] == 5
        assert result.metadata["supports_5ghz"] is False

    def test_too_short_returns_none(self):
        """Manufacturer data < 4 bytes returns None."""
        ad = _make_ad(manufacturer_data=b"\xb5\xb5")
        result = EcoFlowParser().parse(ad)
        assert result is None

    def test_no_manufacturer_data_returns_none(self):
        """No manufacturer data returns None."""
        ad = _make_ad(manufacturer_data=None)
        result = EcoFlowParser().parse(ad)
        assert result is None

    def test_wrong_company_id_returns_none(self):
        """Wrong company ID returns None."""
        payload = _build_full_payload()
        mfr_data = struct.pack("<H", 0x1234) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = EcoFlowParser().parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:ecoflow')[:16]."""
        payload = _build_full_payload()
        ad = _make_ad(
            manufacturer_data=_make_mfr_data(payload),
            mac_address="11:22:33:44:55:66",
        )
        result = EcoFlowParser().parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:ecoflow".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_registry_match_company_id(self):
        """Registry matches on company_id 0xB5B5."""
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_ID,
            local_name_pattern=r"^EF-",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EcoFlowParser):
            pass

        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_registry_match_local_name(self):
        """Registry matches on local name 'EF-...'."""
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_ID,
            local_name_pattern=r"^EF-",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EcoFlowParser):
            pass

        ad = _make_ad(local_name="EF-DELTA2-ABC123")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_raw_payload_hex(self):
        """raw_payload_hex contains the payload after company ID."""
        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.raw_payload_hex == payload.hex()
