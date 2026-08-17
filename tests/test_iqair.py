"""Tests for the IQAir AirVisual plugin.

Ground truth: apk-ble-hunting report ``iqair-airvisual_passive.md``
(``com.airvisual``, Stage 4b).  IQAir advertises a 3-byte identity beacon under
company ID 0x060A — product type, Just-Works pairing flag, pairing mode — plus
a device name that is a substitution-ciphered serial number.  No sensor data
(PM2.5, CO2, temperature, humidity, fan RPM) is ever broadcast.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.iqair import (
    IQAirParser,
    IQAIR_COMPANY_ID,
    PRODUCT_TYPES,
    PAIRING_MODE_FALLBACK,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr(*payload_bytes, company_id=IQAIR_COMPANY_ID):
    return struct.pack("<H", company_id) + bytes(payload_bytes)


def _registry():
    reg = ParserRegistry()

    @register_parser(
        name="iqair", company_id=IQAIR_COMPANY_ID,
        description="IQAir", version="1.0.0", core=False, registry=reg,
    )
    class _P(IQAirParser):
        pass

    return reg


class TestIQAirMatching:
    def test_company_id_is_little_endian_0a06(self):
        """Company ID 0x060A appears on air as `0A 06`."""
        assert IQAIR_COMPANY_ID == 0x060A
        ad = _make_ad(manufacturer_data=bytes.fromhex("0a06") + b"\x0a\x01\x01")
        assert len(_registry().match(ad)) == 1

    def test_wrong_company_id_not_matched(self):
        ad = _make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x01, company_id=0x004C))
        assert _registry().match(ad) == []
        assert IQAirParser().parse(ad) is None

    def test_no_manufacturer_data_returns_none(self):
        assert IQAirParser().parse(_make_ad(local_name="NPWSTHER")) is None


class TestIQAirDecode:
    def test_wire_example_from_report(self):
        """`FF 0A 06 0A 01 01` — AirVisual Pro, Just Works active."""
        ad = _make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x01))
        result = IQAirParser().parse(ad)
        assert result is not None
        assert result.parser_name == "iqair"
        assert result.beacon_type == "iqair"
        assert result.device_class == "sensor"
        assert result.metadata["product_type"] == 10
        assert result.metadata["model_code"] == "AVO2"
        assert result.metadata["device_model"] == "AirVisual Pro"
        assert result.metadata["pairing_just_works"] is True
        assert result.metadata["pairing_mode"] == 1
        assert result.metadata["telemetry"] is False

    @pytest.mark.parametrize("value,code", [
        (4, "KLR"),
        (5, "UI2"),
        (6, "CAP"),
        (10, "AVO2"),
        (11, "WAP"),
    ])
    def test_product_type_table(self, value, code):
        ad = _make_ad(manufacturer_data=_mfr(value, 0x00, 0x00))
        assert IQAirParser().parse(ad).metadata["model_code"] == code
        assert PRODUCT_TYPES[value][0] == code

    def test_unknown_product_type(self):
        ad = _make_ad(manufacturer_data=_mfr(0x63, 0x00, 0x00))
        result = IQAirParser().parse(ad)
        assert result.metadata["product_type"] == 0x63
        assert result.metadata["model_code"] == "unknown"

    def test_just_works_flag_only_when_byte1_is_one(self):
        assert IQAirParser().parse(
            _make_ad(manufacturer_data=_mfr(0x0A, 0x01))
        ).metadata["pairing_just_works"] is True
        assert IQAirParser().parse(
            _make_ad(manufacturer_data=_mfr(0x0A, 0x00))
        ).metadata["pairing_just_works"] is False
        # Only the exact value 1 sets the flag (constructor tests == 1)
        assert IQAirParser().parse(
            _make_ad(manufacturer_data=_mfr(0x0A, 0x02))
        ).metadata["pairing_just_works"] is False

    def test_pairing_mode_byte_only_read_at_length_three(self):
        """x9/d.java:a() reads bArr[2] only when the payload is exactly 3 long."""
        result = IQAirParser().parse(_make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x07)))
        assert result.metadata["pairing_mode"] == 7

    @pytest.mark.parametrize("product,mode", [
        (5, -1),    # UI2
        (10, -2),   # AVO2
        (11, -3),   # WAP
    ])
    def test_pairing_mode_model_fallback(self, product, mode):
        """Models without byte[2] fall back to a negative model-derived mode."""
        result = IQAirParser().parse(_make_ad(manufacturer_data=_mfr(product, 0x00)))
        assert result.metadata["pairing_mode"] == mode
        assert PAIRING_MODE_FALLBACK[product] == mode

    def test_no_pairing_mode_when_no_byte2_and_no_fallback(self):
        result = IQAirParser().parse(_make_ad(manufacturer_data=_mfr(0x04, 0x00)))
        assert "pairing_mode" not in result.metadata

    def test_four_byte_payload_does_not_read_pairing_mode_byte(self):
        result = IQAirParser().parse(_make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x07, 0x09)))
        # length != 3 → model fallback, not bArr[2]
        assert result.metadata["pairing_mode"] == -2

    def test_single_byte_payload_still_gives_product_type(self):
        result = IQAirParser().parse(_make_ad(manufacturer_data=_mfr(0x0A)))
        assert result.metadata["product_type"] == 10
        assert "pairing_just_works" not in result.metadata

    def test_empty_payload_returns_none(self):
        assert IQAirParser().parse(_make_ad(manufacturer_data=b"\x0a\x06")) is None


class TestIQAirName:
    def test_encoded_name_strips_non_alphanumerics(self):
        """Step 1-2 of x9/d.java:d(): strip non-alphanumerics from the name."""
        ad = _make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x01),
                      local_name="NPWS-THER 1234")
        result = IQAirParser().parse(ad)
        assert result.metadata["encoded_name"] == "NPWSTHER1234"

    def test_serial_is_not_guessed(self):
        """The report's substitution table is partial and self-contradictory
        (S→5 or 0, H→5 vs E→6 vs T→6), so no plaintext serial is emitted."""
        ad = _make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x01), local_name="NPWSTHER")
        assert "serial_number" not in IQAirParser().parse(ad).metadata

    def test_identity_hash_prefers_encoded_name(self):
        """The ciphered name carries a per-unit serial; it beats the MAC."""
        expected = hashlib.sha256(b"iqair:NPWSTHER1234").hexdigest()[:16]
        a = IQAirParser().parse(_make_ad(
            manufacturer_data=_mfr(0x0A, 0x01, 0x01),
            local_name="NPWS-THER1234", mac_address="11:22:33:44:55:66"))
        b = IQAirParser().parse(_make_ad(
            manufacturer_data=_mfr(0x0A, 0x01, 0x01),
            local_name="NPWSTHER1234", mac_address="AA:BB:CC:DD:EE:FF"))
        assert a.identifier_hash == expected
        assert b.identifier_hash == expected

    def test_identity_hash_falls_back_to_mac(self):
        result = IQAirParser().parse(_make_ad(
            manufacturer_data=_mfr(0x0A, 0x01, 0x01), mac_address="11:22:33:44:55:66"))
        assert result.identifier_hash == hashlib.sha256(
            b"iqair:mac:11:22:33:44:55:66"
        ).hexdigest()[:16]

    def test_raw_payload_hex(self):
        ad = _make_ad(manufacturer_data=_mfr(0x0A, 0x01, 0x01))
        assert IQAirParser().parse(ad).raw_payload_hex == "0a0101"
