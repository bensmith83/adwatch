"""Tests for the iTENS (Brighteye Innovations) TENS plugin.

Per apk-ble-hunting/reports/brighteye-itens_passive.md. Discovery fingerprint
(`f0/h.java:40-93`) requires ALL of:
  1. manufacturer data under company ID 12357 (0x3045), length >= 1
  2. advertised service UUID 0xFFF0
  3. advertised service UUID 0xFFB0

Two manufacturer payload shapes: a 7-byte little-endian binary frame (when
0x5000 is also advertised) or an ASCII ``EM<digits>`` identifier.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.itens import ITensParser, ITENS_COMPANY_ID


FFF0 = "0000fff0-0000-1000-8000-00805f9b34fb"
FFB0 = "0000ffb0-0000-1000-8000-00805f9b34fb"
PROP_5000 = "00005000-0000-1000-8000-00805f9b34fb"


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "A4:C1:38:11:22:33",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
        "service_uuids": [FFF0, FFB0],
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _mfr(payload: bytes) -> bytes:
    """Company ID 0x3045 little-endian (raw `45 30`) + payload."""
    return ITENS_COMPANY_ID.to_bytes(2, "little") + payload


def _binary_frame(l=0x1234, q=0x11, p=0x22, n=0x33, o=0x44, m=0x55) -> bytes:
    return bytes([l & 0xFF, (l >> 8) & 0xFF, q, p, n, o, m])


def _register(registry):
    @register_parser(
        name="itens",
        company_id=ITENS_COMPANY_ID,
        description="iTENS",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ITensParser):
        pass

    return _P


class TestITensMatching:
    def test_company_id_is_little_endian_4530(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        assert ad.manufacturer_data[:2] == bytes.fromhex("4530")
        assert ad.company_id == 0x3045 == 12357

    def test_matches_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        assert len(registry.match(ad)) == 1

    def test_does_not_match_byteswapped_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes.fromhex("3045") + b"\x01")
        assert registry.match(ad) == []


class TestITensFingerprint:
    def test_requires_both_service_uuids(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()), service_uuids=[FFF0])
        assert ITensParser().parse(ad) is None

    def test_requires_ffb0_too(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()), service_uuids=[FFB0])
        assert ITensParser().parse(ad) is None

    def test_accepts_short_16bit_uuid_forms(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()),
                      service_uuids=["fff0", "ffb0"])
        assert ITensParser().parse(ad) is not None

    def test_rejects_empty_manufacturer_payload(self):
        """The app requires a byte array of length >= 1."""
        ad = _make_ad(manufacturer_data=_mfr(b""))
        assert ITensParser().parse(ad) is None

    def test_rejects_wrong_company_id(self):
        ad = _make_ad(manufacturer_data=bytes.fromhex("4c00") + b"\x01")
        assert ITensParser().parse(ad) is None

    def test_rejects_missing_manufacturer_data(self):
        assert ITensParser().parse(_make_ad()) is None


class TestITensFormatABinary:
    def test_decodes_seven_byte_frame(self):
        ad = _make_ad(
            manufacturer_data=_mfr(_binary_frame()),
            service_uuids=[FFF0, FFB0, PROP_5000],
        )
        result = ITensParser().parse(ad)
        assert result is not None
        assert result.metadata["payload_format"] == "binary"
        assert result.metadata["field_l"] == 0x1234
        assert result.metadata["field_q"] == 0x11
        assert result.metadata["field_p"] == 0x22
        assert result.metadata["field_n"] == 0x33
        assert result.metadata["field_o"] == 0x44
        assert result.metadata["field_m"] == 0x55

    def test_field_l_is_little_endian(self):
        ad = _make_ad(
            manufacturer_data=_mfr(bytes([0xCD, 0xAB, 0, 0, 0, 0, 0])),
            service_uuids=[FFF0, FFB0, PROP_5000],
        )
        assert ITensParser().parse(ad).metadata["field_l"] == 0xABCD

    def test_field_semantics_marked_unknown(self):
        """Obfuscated single-letter names — semantics must not be invented."""
        ad = _make_ad(
            manufacturer_data=_mfr(_binary_frame()),
            service_uuids=[FFF0, FFB0, PROP_5000],
        )
        assert ITensParser().parse(ad).metadata["field_semantics"] == "unknown"

    def test_binary_frame_without_5000_still_decodes(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        result = ITensParser().parse(ad)
        assert result.metadata["payload_format"] == "binary"
        assert result.metadata["field_l"] == 0x1234

    def test_proprietary_service_flag(self):
        with_5000 = _make_ad(
            manufacturer_data=_mfr(_binary_frame()),
            service_uuids=[FFF0, FFB0, PROP_5000],
        )
        without = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        assert ITensParser().parse(with_5000).metadata["proprietary_service"] is True
        assert ITensParser().parse(without).metadata["proprietary_service"] is False

    def test_short_payload_is_unknown_format(self):
        ad = _make_ad(manufacturer_data=_mfr(b"\x01\x02\x03"))
        result = ITensParser().parse(ad)
        assert result is not None
        assert result.metadata["payload_format"] == "unknown"
        assert "field_l" not in result.metadata


class TestITensFormatBAscii:
    def test_decodes_em_identifier(self):
        ad = _make_ad(manufacturer_data=_mfr(b"EM12345"))
        result = ITensParser().parse(ad)
        assert result.metadata["payload_format"] == "ascii_em"
        assert result.metadata["model_id"] == 12345

    def test_ascii_takes_priority_when_5000_absent(self):
        """7 ASCII bytes could also look like a binary frame."""
        ad = _make_ad(manufacturer_data=_mfr(b"EM00007"))
        assert ITensParser().parse(ad).metadata["payload_format"] == "ascii_em"

    def test_binary_wins_when_5000_advertised(self):
        ad = _make_ad(
            manufacturer_data=_mfr(b"EM12345"),
            service_uuids=[FFF0, FFB0, PROP_5000],
        )
        assert ITensParser().parse(ad).metadata["payload_format"] == "binary"

    def test_identity_prefers_em_id(self):
        ad = _make_ad(manufacturer_data=_mfr(b"EM12345"))
        result = ITensParser().parse(ad)
        expected = hashlib.sha256(b"itens:em12345").hexdigest()[:16]
        assert result.identifier_hash == expected
        assert result.metadata["identity_basis"] == "em_id"

    def test_em_identity_survives_mac_rotation(self):
        a = ITensParser().parse(
            _make_ad(manufacturer_data=_mfr(b"EM12345"), mac_address="A4:C1:38:11:22:33"))
        b = ITensParser().parse(
            _make_ad(manufacturer_data=_mfr(b"EM12345"), mac_address="DE:AD:BE:EF:00:01"))
        assert a.identifier_hash == b.identifier_hash


class TestITensResult:
    def test_result_shape(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        result = ITensParser().parse(ad)
        assert result.parser_name == "itens"
        assert result.beacon_type == "itens"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "iTENS"
        assert result.metadata["company_id"] == 0x3045

    def test_flags_sensitive_category(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        result = ITensParser().parse(ad)
        assert result.metadata["sensitive"] is True
        assert result.metadata["sensitive_category"] == "pain_therapy"

    def test_local_name_is_not_a_match_criterion(self):
        """The app parses the name but ignores it for matching."""
        ad = _make_ad(manufacturer_data=None, service_uuids=[FFF0, FFB0],
                      local_name="iTENS")
        assert ITensParser().parse(ad) is None

    def test_identity_falls_back_to_mac(self):
        ad = _make_ad(manufacturer_data=_mfr(_binary_frame()))
        result = ITensParser().parse(ad)
        expected = hashlib.sha256(b"itens:A4:C1:38:11:22:33").hexdigest()[:16]
        assert result.identifier_hash == expected
        assert result.metadata["identity_basis"] == "mac"

    def test_raw_payload_hex_is_full_mfr_data(self):
        ad = _make_ad(manufacturer_data=_mfr(b"\xaa"))
        assert ITensParser().parse(ad).raw_payload_hex == "4530aa"

    def test_storage_schema_is_none(self):
        assert ITensParser().storage_schema() is None
