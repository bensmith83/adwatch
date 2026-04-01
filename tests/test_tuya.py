"""Tests for Tuya / Smart Life BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tuya import TuyaParser, TUYA_COMPANY_ID


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
        name="tuya",
        company_id=TUYA_COMPANY_ID,
        description="Tuya / Smart Life BLE advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(TuyaParser):
        pass

    return registry


def _tuya_mfr_data(protocol_version=0x03, flags=0x00, product_id=b""):
    """Build manufacturer data: company_id (LE) + protocol_version + flags + product_id."""
    payload = bytes([protocol_version, flags]) + product_id
    return TUYA_COMPANY_ID.to_bytes(2, "little") + payload


class TestTuyaParser:
    # --- Registry matching ---

    def test_matches_company_id_0x07D0(self):
        """Matches on Tuya company_id 0x07D0."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    # --- Basic fields ---

    def test_parser_name(self):
        """parser_name is 'tuya'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "tuya"

    def test_beacon_type(self):
        """beacon_type is 'tuya'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "tuya"

    def test_device_class_smart_home(self):
        """device_class is 'smart_home'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result.device_class == "smart_home"

    # --- Manufacturer data parsing ---

    def test_protocol_version_from_payload(self):
        """metadata['protocol_version'] is byte 0 of payload."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(protocol_version=0x05))
        result = parser.parse(ad)
        assert result.metadata["protocol_version"] == 0x05

    def test_flags_from_payload(self):
        """metadata['flags'] is byte 1 of payload."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x42))
        result = parser.parse(ad)
        assert result.metadata["flags"] == 0x42

    # --- Pairing flag detection ---

    def test_pairing_true_when_flag_bit0_set(self):
        """flags=0x01 -> metadata['pairing'] = True."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x01))
        result = parser.parse(ad)
        assert result.metadata["pairing"] is True

    def test_pairing_false_when_flag_bit0_clear(self):
        """flags=0x00 -> metadata['pairing'] = False."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x00))
        result = parser.parse(ad)
        assert result.metadata["pairing"] is False

    def test_pairing_true_when_flag_bit0_set_with_other_bits(self):
        """flags=0x03 (bit 0 set) -> metadata['pairing'] = True."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x03))
        result = parser.parse(ad)
        assert result.metadata["pairing"] is True

    # --- Product ID ---

    def test_product_id_hex_present(self):
        """product_id=b'\\xAB\\xCD\\xEF' -> metadata['product_id_hex'] = 'abcdef'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(product_id=b"\xAB\xCD\xEF"))
        result = parser.parse(ad)
        assert result.metadata["product_id_hex"] == "abcdef"

    def test_product_id_hex_absent_when_no_extra_bytes(self):
        """No product_id bytes (just 2-byte payload) -> 'product_id_hex' not in metadata."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(product_id=b""))
        result = parser.parse(ad)
        assert "product_id_hex" not in result.metadata

    # --- Local name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to raw local_name value."""
        parser = TuyaParser()
        ad = _make_ad(
            manufacturer_data=_tuya_mfr_data(),
            local_name="TY-SmartPlug",
        )
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "TY-SmartPlug"

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:tuya)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:tuya".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex(self):
        """raw_payload_hex contains hex of manufacturer payload (without company_id)."""
        parser = TuyaParser()
        payload_bytes = bytes([0x03, 0x00]) + b"\xAB\xCD"
        ad = _make_ad(manufacturer_data=TUYA_COMPANY_ID.to_bytes(2, "little") + payload_bytes)
        result = parser.parse(ad)
        assert result.raw_payload_hex == payload_bytes.hex()

    # --- Edge cases ---

    def test_returns_none_wrong_company_id(self):
        """Returns None when company_id is not Tuya."""
        parser = TuyaParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = TuyaParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_payload(self):
        """Returns None when payload < 2 bytes (company_id + 1 byte only)."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=TUYA_COMPANY_ID.to_bytes(2, "little") + b"\x01")
        result = parser.parse(ad)
        assert result is None

    def test_handles_local_name_none(self):
        """Parses successfully with local_name=None."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "tuya"
        assert "local_name" not in result.metadata or result.metadata.get("local_name") is None
