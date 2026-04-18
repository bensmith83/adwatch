"""Tests for August/Yale smart lock plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.august_yale import AugustYaleParser


# Service UUIDs per apk-ble-hunting/reports/august-luna_passive.md and
# assaabloy-yale_passive.md — V1/V2/V3/V4 lock generations plus keypad UUIDs.
V1_UUID = "bd4ac610-0b45-11e3-8ffd-0800200c9a66"
V2_UUID = "e295c550-69d0-11e4-b116-123b93f75cba"
V3_UUID = "fe24"
V4_UUID = "fcbf"
KEYPAD_UUID = "52e4c6be-0f96-425c-8900-ddcef680f636"
KEYPAD_OTA_UUID = "a86abc2d-d44c-442e-99f7-80059a873e36"

COMPANY_IDS = [0x0016, 0x01D1, 0x012E, 0x0BDE]
SERVICE_UUIDS = [V1_UUID, V2_UUID, V3_UUID, V4_UUID, KEYPAD_UUID, KEYPAD_OTA_UUID]
KEYPAD_NAME_RE = r"^(?:Keypad|August|ASSA ABLOY) (K\d[a-zA-Z0-9]{8})$"


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


def _build_mfr_data(company_id=0x01D1, payload=b""):
    return struct.pack("<H", company_id) + payload


def _register(registry):
    @register_parser(
        name="august_yale",
        company_id=COMPANY_IDS,
        service_uuid=SERVICE_UUIDS,
        local_name_pattern=KEYPAD_NAME_RE,
        description="August/Yale",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(AugustYaleParser):
        pass

    return _P


class TestAugustYaleMatching:
    def test_match_legacy_august_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x0016, b"\x00"))
        assert len(registry.match(ad)) == 1

    def test_match_august_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x01D1, b"\x00"))
        assert len(registry.match(ad)) == 1

    def test_match_assa_abloy_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x012E, b"\x00"))
        assert len(registry.match(ad)) == 1

    def test_match_legacy_bde_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x0BDE, b"\x00"))
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid_v3(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[V3_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid_v4(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[V4_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid_v2_128bit(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[V2_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid_v1_128bit(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[V1_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_keypad_name_august(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="August K1AB23CD45")
        assert len(registry.match(ad)) == 1

    def test_match_keypad_name_assa_abloy(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="ASSA ABLOY K2XY98ZW76")
        assert len(registry.match(ad)) == 1

    def test_match_keypad_name_plain(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Keypad K0DE12FG34")
        assert len(registry.match(ad)) == 1


class TestAugustYaleParsing:
    def _parse(self, **ad_kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**ad_kwargs)
        matched = registry.match(ad)
        assert matched, f"no parser matched ad: {ad}"
        return matched[0].parse(ad)

    def test_state_toggle_from_header_byte(self):
        # Backward-compat: the original parser stored payload[0] as state_toggle.
        # Kept as-is to avoid breaking downstream metadata consumers.
        result = self._parse(
            manufacturer_data=_build_mfr_data(0x01D1, bytes([0x01])),
            local_name="A112345",
        )
        assert result.metadata["state_toggle"] == 0x01

    def test_lock_id_extraction_august_legacy(self):
        lock_id_bytes = bytes(range(16))
        payload = b"\xaa\xbb" + lock_id_bytes  # 2-byte header + 16 byte LockID
        result = self._parse(manufacturer_data=_build_mfr_data(0x0016, payload))
        assert result.metadata["lock_id"] == lock_id_bytes.hex()

    def test_lock_id_extraction_yale_assa_abloy(self):
        lock_id_bytes = bytes(range(0x20, 0x30))
        payload = b"\x00\x00" + lock_id_bytes
        result = self._parse(manufacturer_data=_build_mfr_data(0x012E, payload))
        assert result.metadata["lock_id"] == lock_id_bytes.hex()

    def test_lock_id_extraction_tail_aligned_id465(self):
        lock_id_bytes = bytes(range(0x40, 0x50))
        payload = b"\x99" * 4 + lock_id_bytes  # tail-aligned
        result = self._parse(manufacturer_data=_build_mfr_data(0x01D1, payload))
        assert result.metadata["lock_id"] == lock_id_bytes.hex()

    def test_lock_id_absent_when_payload_too_short(self):
        # IDs 22/76/302 require >= 18 bytes of mfr payload for header + 16-byte ID.
        payload = b"\xaa\xbb" + bytes(range(8))  # only 10 bytes total
        result = self._parse(manufacturer_data=_build_mfr_data(0x0016, payload))
        assert "lock_id" not in result.metadata

    def test_generation_v3_from_fe24(self):
        result = self._parse(service_uuids=[V3_UUID])
        assert result.metadata["generation"] == "V3_2017"

    def test_generation_v4_from_fcbf(self):
        result = self._parse(service_uuids=[V4_UUID])
        assert result.metadata["generation"] == "V4_2023"

    def test_generation_v2_from_128bit(self):
        result = self._parse(service_uuids=[V2_UUID])
        assert result.metadata["generation"] == "V2_2014"

    def test_generation_v1_from_128bit(self):
        result = self._parse(service_uuids=[V1_UUID])
        assert result.metadata["generation"] == "V1_2014"

    def test_keypad_detected_from_name(self):
        result = self._parse(local_name="August K1AB23CD45")
        assert result.metadata["device_kind"] == "keypad"
        assert result.metadata["keypad_serial"] == "K1AB23CD45"

    def test_keypad_serial_assa_abloy_prefix(self):
        result = self._parse(local_name="ASSA ABLOY K2XY98ZW76")
        assert result.metadata["keypad_serial"] == "K2XY98ZW76"

    def test_identity_hash_uses_lock_id_when_available(self):
        lock_id_bytes = bytes(range(16))
        payload = b"\xaa\xbb" + lock_id_bytes
        result = self._parse(
            manufacturer_data=_build_mfr_data(0x0016, payload),
            mac_address="11:22:33:44:55:66",
            local_name="Front Door",
        )
        expected = hashlib.sha256(
            f"august_yale:lockid:{lock_id_bytes.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_falls_back_without_lock_id(self):
        # Short mfr data → no lock_id; fall back to mac:local_name.
        result = self._parse(
            manufacturer_data=_build_mfr_data(0x01D1, b"\x00"),
            mac_address="11:22:33:44:55:66",
            local_name="A112345",
        )
        expected = hashlib.sha256("11:22:33:44:55:66:A112345".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_uses_keypad_serial(self):
        # No mfr data, just keypad name.
        result = self._parse(
            local_name="August K1AB23CD45",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        expected = hashlib.sha256(
            "august_yale:keypad:K1AB23CD45".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class_lock_by_default(self):
        result = self._parse(
            manufacturer_data=_build_mfr_data(0x01D1, b"\x00"),
            local_name="A112345",
        )
        assert result.device_class == "lock"

    def test_device_class_keypad_when_serial_detected(self):
        result = self._parse(local_name="Keypad K0DE12FG34")
        assert result.device_class == "keypad"

    def test_beacon_type(self):
        result = self._parse(
            manufacturer_data=_build_mfr_data(0x01D1, b"\x00"),
            local_name="A112345",
        )
        assert result.beacon_type == "august_yale"
