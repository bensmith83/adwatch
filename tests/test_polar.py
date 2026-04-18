"""Tests for Polar fitness device plugin.

Identifiers per apk-ble-hunting/reports/polar-polarflow_passive.md.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.polar import (
    PolarParser,
    POLAR_COMPANY_ID,
    POLAR_SERVICE_UUID,
    _decode_user_id,
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


def _valid_broadcast(user_id: int = 12345678, user_id_len: int = 6, total_len: int = 13) -> bytes:
    """Build a valid PbMasterIdentifierBroadcast mfr payload.

    Parser expects: SF byte at [2] with bits 4,5,6 set & 3,7 clear (0x70),
    user_id_len at [3], reversed-BE user_id bytes at [4..4+user_id_len].
    """
    if user_id == 0:
        user_bytes_reversed = bytes(user_id_len)
    else:
        # encode big-endian with leading zeros, then reverse (the parser reverses
        # wire-bytes back to big-endian, so we pre-reverse big-endian here).
        be = user_id.to_bytes(user_id_len, "big")
        user_bytes_reversed = be[::-1]
    header = bytes([0x00, 0x00, 0x70, user_id_len])
    body = user_bytes_reversed
    padding = bytes(max(0, total_len - len(header) - len(body)))
    return struct.pack("<H", POLAR_COMPANY_ID) + header + body + padding


@pytest.fixture
def parser():
    return PolarParser()


class TestPolarUserIdDecode:
    def test_decode_valid_user_id(self):
        payload = _valid_broadcast(user_id=12345678)[2:]
        assert _decode_user_id(payload) == 12345678

    def test_decode_zero_user_id_ftu(self):
        payload = _valid_broadcast(user_id=0)[2:]
        assert _decode_user_id(payload) == 0

    def test_decode_invalid_sf_byte(self):
        # Flip bit 7 on the SF byte.
        ad_bytes = bytearray(_valid_broadcast()[2:])
        ad_bytes[2] |= 0x80
        assert _decode_user_id(bytes(ad_bytes)) is None

    def test_decode_sf_bit_3_set_invalid(self):
        ad_bytes = bytearray(_valid_broadcast()[2:])
        ad_bytes[2] |= 0x08
        assert _decode_user_id(bytes(ad_bytes)) is None

    def test_decode_missing_user_id_bytes(self):
        payload = bytes([0x00, 0x00, 0x70, 0x10])  # claim 16 bytes user_id
        assert _decode_user_id(payload) is None


class TestPolarDetection:
    def test_matches_company_id(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast())
        result = parser.parse(ad)
        assert result is not None

    def test_matches_service_uuid(self, parser):
        ad = _make_ad(service_uuids=[POLAR_SERVICE_UUID])
        result = parser.parse(ad)
        assert result is not None

    def test_matches_name_prefix(self, parser):
        ad = _make_ad(local_name="Polar H10 AABBCCDD")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model_family"] == "H10"
        assert result.metadata["serial"] == "AABBCCDD"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="Random Device")) is None


class TestPolarMetadata:
    def test_bonded_user_id_exposed(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast(user_id=42))
        result = parser.parse(ad)
        assert result.metadata["flow_user_id"] == 42
        assert result.metadata["pairing_state"] == "bonded"

    def test_ftu_zero_user_id(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast(user_id=0))
        result = parser.parse(ad)
        assert result.metadata["pairing_state"] == "ftu"
        assert "flow_user_id" not in result.metadata

    def test_watch_tier_from_13_byte_payload(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast(total_len=13))
        result = parser.parse(ad)
        assert result.metadata["product_tier_hint"] == "watch"

    def test_strap_tier_from_11_byte_payload(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast(total_len=11))
        result = parser.parse(ad)
        assert result.metadata["product_tier_hint"] == "strap_or_armband"

    def test_model_family_and_serial_from_name(self, parser):
        ad = _make_ad(local_name="Polar Vantage V2 12345678")
        result = parser.parse(ad)
        assert result.metadata["model_family"] == "Vantage V2"
        assert result.metadata["serial"] == "12345678"

    def test_gopro_paired_flag(self, parser):
        ad = _make_ad(
            local_name="Polar H10 AABBCCDD",
            service_uuids=["a5fe"],
        )
        result = parser.parse(ad)
        assert result.metadata["gopro_paired"] is True


class TestPolarIdentity:
    def test_identity_hash_uses_flow_user_id(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast(user_id=99))
        result = parser.parse(ad)
        expected = hashlib.sha256("polar:flow_user:99".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_falls_back_to_serial(self, parser):
        ad = _make_ad(local_name="Polar H10 SERIAL01")
        result = parser.parse(ad)
        expected = hashlib.sha256("polar:serial:SERIAL01".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestPolarFields:
    def test_device_class(self, parser):
        ad = _make_ad(local_name="Polar H10 AABBCCDD")
        assert parser.parse(ad).device_class == "wearable"

    def test_parser_name(self, parser):
        ad = _make_ad(manufacturer_data=_valid_broadcast())
        assert parser.parse(ad).parser_name == "polar"
