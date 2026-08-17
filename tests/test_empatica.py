"""Tests for the Empatica EmbracePlus plugin.

Byte layout per apk-ble-hunting/reports/empatica-healthmonitor-epilepsy_passive.md:
name contains "Embrace" + a manufacturer-data block >= 24 bytes (offsets are
into the block *after* the 2-byte company ID, i.e. straight into
`RawAdvertisement.manufacturer_payload`):

    [7..16]  ASCII serial (10 chars) -> model + hardware variant
    [19]&0x3 pairing mode
    [20]     quick-pairing mode
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.empatica import (
    EmpaticaParser,
    EMPATICA_COMPANY_ID,
    EMPATICA_SERVICE_UUID,
    SERIAL_OFFSET,
    SERIAL_LENGTH,
    MIN_PAYLOAD_LEN,
    decode_model,
    decode_variant,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "Embrace 1234",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _payload(serial="3CABCDEFGH", pairing=1, quick=3,
             header=b"\x11" * 7, mid=b"\x00\x00", tail=b"\x00\x00\x00") -> bytes:
    return header + serial.encode("ascii") + mid + bytes([pairing, quick]) + tail


def _mfr(payload: bytes, company_id: int = EMPATICA_COMPANY_ID) -> bytes:
    return struct.pack("<H", company_id) + payload


def _register(registry):
    @register_parser(
        name="empatica",
        company_id=EMPATICA_COMPANY_ID,
        local_name_pattern=r"(?i)embrace",
        description="Empatica",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(EmpaticaParser):
        pass

    return _P


class TestEmpaticaConstants:
    def test_company_id(self):
        assert EMPATICA_COMPANY_ID == 0x02D1

    def test_service_uuid(self):
        assert EMPATICA_SERVICE_UUID == "3ea00001-e0e2-e4ff-9069-6a7f0ae28705"

    def test_layout_constants(self):
        assert SERIAL_OFFSET == 7
        assert SERIAL_LENGTH == 10
        assert MIN_PAYLOAD_LEN == 24

    def test_payload_helper_is_24_bytes(self):
        assert len(_payload()) == 24


class TestSerialDecode:
    def test_model_from_first_char(self):
        assert decode_model("1ABCDEFGHI") == "EMBRACE1"
        assert decode_model("2ABCDEFGHI") == "EMBRACE2"
        assert decode_model("3ABCDEFGHI") == "EMBRACE_PLUS"
        assert decode_model("4ABCDEFGHI") == "EMBRACE_PLUS"
        assert decode_model("XABCDEFGHI") == "UNKNOWN"
        assert decode_model("") == "UNKNOWN"

    def test_variant_mini_when_serial_contains_4(self):
        assert decode_variant("4ABCDEFGHI") == "EMBRACE_MINI"
        assert decode_variant("3AB4DEFGHI") == "EMBRACE_MINI"

    def test_variant_mini_from_regex(self):
        assert decode_variant("3YMABYYZZZ") == "EMBRACE_MINI"

    def test_variant_v2(self):
        assert decode_variant("3CABCDEFGH") == "EMBRACE_PLUS_V2"

    def test_variant_plain_plus(self):
        assert decode_variant("3ABCDEFGHI") == "EMBRACE_PLUS"

    def test_variant_none_for_older_models(self):
        assert decode_variant("1ABCDEFGHI") is None


class TestEmpaticaMatching:
    def test_match_name_substring(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Embrace Plus 42"))) == 1

    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name=None, manufacturer_data=_mfr(_payload()))
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Fitbit Charge",
                      manufacturer_data=_mfr(_payload(), company_id=0x004C))
        assert registry.match(ad) == []


class TestEmpaticaParse:
    def test_full_decode(self):
        result = EmpaticaParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(serial="3CABCDEFGH",
                                                     pairing=2, quick=1)))
        )
        assert result is not None
        assert result.parser_name == "empatica"
        assert result.device_class == "medical"
        assert result.metadata["serial"] == "3CABCDEFGH"
        assert result.metadata["model"] == "EMBRACE_PLUS"
        assert result.metadata["hardware_variant"] == "EMBRACE_PLUS_V2"
        assert result.metadata["pairing_mode"] == 2
        assert result.metadata["quick_pairing_mode"] == 1
        assert result.metadata["pairing_mode_valid"] is True
        assert result.metadata["quick_pairing_mode_valid"] is True

    def test_pairing_mode_masks_high_bits(self):
        result = EmpaticaParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(pairing=0xF2)))
        )
        assert result.metadata["pairing_mode"] == 2

    def test_invalid_pairing_values_flagged(self):
        result = EmpaticaParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(pairing=0x03, quick=0x07)))
        )
        assert result.metadata["pairing_mode"] == 3
        assert result.metadata["pairing_mode_valid"] is False
        assert result.metadata["quick_pairing_mode_valid"] is False

    def test_mini_variant(self):
        result = EmpaticaParser().parse(
            _make_ad(manufacturer_data=_mfr(_payload(serial="4ABCDEFGHI")))
        )
        assert result.metadata["hardware_variant"] == "EMBRACE_MINI"

    def test_identity_hash_uses_serial_not_mac(self):
        payload = _payload(serial="3CABCDEFGH")
        a = EmpaticaParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        b = EmpaticaParser().parse(
            _make_ad(mac_address="11:22:33:44:55:66",
                     manufacturer_data=_mfr(payload))
        )
        expected = hashlib.sha256(b"empatica:3CABCDEFGH").hexdigest()[:16]
        assert a.identifier_hash == expected
        assert a.identifier_hash == b.identifier_hash

    def test_identity_falls_back_to_mac_without_payload(self):
        result = EmpaticaParser().parse(_make_ad(local_name="Embrace"))
        expected = hashlib.sha256(b"empatica:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_name_only_presence_record(self):
        result = EmpaticaParser().parse(_make_ad(local_name="Embrace"))
        assert result is not None
        assert result.metadata["device_name"] == "Embrace"
        assert "serial" not in result.metadata

    def test_short_payload_is_not_decoded(self):
        result = EmpaticaParser().parse(
            _make_ad(manufacturer_data=_mfr(b"\x00" * 20))
        )
        assert result is not None
        assert "serial" not in result.metadata
        assert result.metadata["payload_length"] == 20

    def test_non_ascii_serial_is_skipped(self):
        payload = bytearray(_payload())
        payload[SERIAL_OFFSET] = 0xFF
        result = EmpaticaParser().parse(_make_ad(manufacturer_data=_mfr(bytes(payload))))
        assert result is not None
        assert "serial" not in result.metadata

    def test_service_uuid_match_parses(self):
        result = EmpaticaParser().parse(
            _make_ad(local_name=None, service_uuids=[EMPATICA_SERVICE_UUID])
        )
        assert result is not None

    def test_unrelated_returns_none(self):
        result = EmpaticaParser().parse(
            _make_ad(local_name="Galaxy Watch",
                     manufacturer_data=_mfr(_payload(), company_id=0x0075))
        )
        assert result is None

    def test_raw_payload_hex_present(self):
        payload = _payload()
        result = EmpaticaParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert result.raw_payload_hex == payload.hex()
