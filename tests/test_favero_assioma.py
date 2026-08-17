"""Tests for Favero Assioma power-meter pedal plugin.

Byte layout per apk-ble-hunting/reports/favero-assioma_passive.md.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.favero_assioma import (
    FaveroAssiomaParser,
    FAVERO_COMPANY_ID,
    FAVERO_NAME_PATTERN,
    MODEL_PREFIXES,
    SIDE_CODES,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-08-16T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr(payload: bytes) -> bytes:
    return struct.pack("<H", FAVERO_COMPANY_ID) + payload


def _register(registry):
    @register_parser(
        name="favero_assioma",
        company_id=FAVERO_COMPANY_ID,
        local_name_pattern=FAVERO_NAME_PATTERN,
        description="Favero Assioma",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(FaveroAssiomaParser):
        pass

    return registry


class TestMatching:
    def test_company_id_is_favero_electronics(self):
        assert FAVERO_COMPANY_ID == 0x0364

    def test_matches_company_id(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(manufacturer_data=_mfr(b"\x01\x02\x03")))) == 1

    def test_matches_little_endian_cid_on_the_wire(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(manufacturer_data=bytes.fromhex("6403010203"))
        assert len(reg.match(ad)) == 1

    def test_matches_name_prefixes(self):
        reg = _register(ParserRegistry())
        for name in ("ASSIOMA12345", "AssiomaPRO9911", "A2-L0042",
                     "A3-R0042", "A4-U0042"):
            assert len(reg.match(_make_ad(local_name=name))) == 1, name

    def test_ignores_wrong_cid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(manufacturer_data=struct.pack("<H", 0x004C) + b"\x02\x15")
        assert reg.match(ad) == []

    def test_ignores_short_lookalike_name(self):
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(local_name="A2-")) == []


class TestManufacturerDecode:
    def test_variant_byte_is_payload_index_2(self):
        r = FaveroAssiomaParser().parse(_make_ad(manufacturer_data=_mfr(b"\xaa\xbb\x07\xcc")))
        assert r is not None
        assert r.metadata["variant_byte"] == 0x07
        assert r.metadata["variant_code"] == 7

    def test_variant_byte_is_signed_like_the_app(self):
        r = FaveroAssiomaParser().parse(_make_ad(manufacturer_data=_mfr(b"\x00\x00\xff")))
        assert r.metadata["variant_byte"] == 0xFF
        assert r.metadata["variant_code"] == -1

    def test_short_payload_has_no_variant(self):
        r = FaveroAssiomaParser().parse(_make_ad(manufacturer_data=_mfr(b"\x00\x01")))
        assert r is not None
        assert "variant_code" not in r.metadata

    def test_raw_payload_hex_recorded(self):
        r = FaveroAssiomaParser().parse(_make_ad(manufacturer_data=_mfr(b"\x01\x02\x03")))
        assert r.raw_payload_hex == "010203"


class TestNameDecode:
    def test_all_model_prefixes_resolve(self):
        p = FaveroAssiomaParser()
        for prefix, model in MODEL_PREFIXES:
            r = p.parse(_make_ad(local_name=f"{prefix}12345"))
            assert r is not None, prefix
            assert r.metadata["model"] == model
            assert r.metadata["serial"] == "12345"

    def test_pro_prefix_wins_over_legacy(self):
        r = FaveroAssiomaParser().parse(_make_ad(local_name="AssiomaPRO7788"))
        assert r.metadata["model"] == "PRO"
        assert r.metadata["serial"] == "7788"

    def test_side_from_serial_leading_letter(self):
        p = FaveroAssiomaParser()
        assert p.parse(_make_ad(local_name="A3-L1234")).metadata["side"] == SIDE_CODES["L"]
        assert p.parse(_make_ad(local_name="A3-R1234")).metadata["side"] == SIDE_CODES["R"]
        assert p.parse(_make_ad(local_name="A3-U1234")).metadata["side"] == SIDE_CODES["U"]

    def test_no_side_letter(self):
        r = FaveroAssiomaParser().parse(_make_ad(local_name="A3-1234"))
        assert "side" not in r.metadata

    def test_device_class(self):
        r = FaveroAssiomaParser().parse(_make_ad(local_name="ASSIOMA12345"))
        assert r.device_class == "fitness_sensor"
        assert r.metadata["telemetry"] == "connect_required_0x2A63"


class TestIdentity:
    def test_serial_beats_mac(self):
        p = FaveroAssiomaParser()
        a = _make_ad(mac_address="11:22:33:44:55:66", local_name="A3-L1234")
        b = _make_ad(mac_address="99:88:77:66:55:44", local_name="A3-L1234")
        assert p.parse(a).identifier_hash == p.parse(b).identifier_hash
        assert p.parse(a).identifier_hash == hashlib.sha256(
            b"favero:A3:L1234").hexdigest()[:16]

    def test_left_and_right_pedals_are_distinct(self):
        p = FaveroAssiomaParser()
        left = p.parse(_make_ad(local_name="A3-L1234"))
        right = p.parse(_make_ad(local_name="A3-R1234"))
        assert left.identifier_hash != right.identifier_hash

    def test_mac_fallback_when_only_cid(self):
        r = FaveroAssiomaParser().parse(_make_ad(manufacturer_data=_mfr(b"\x00\x00\x05")))
        assert r.identifier_hash == hashlib.sha256(
            b"favero:AA:BB:CC:DD:EE:FF").hexdigest()[:16]

    def test_returns_none_for_unrelated(self):
        assert FaveroAssiomaParser().parse(
            _make_ad(local_name="A1-9999",
                     manufacturer_data=struct.pack("<H", 0x004C))) is None
