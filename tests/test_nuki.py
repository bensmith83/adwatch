"""Tests for Nuki smart lock / bridge / fob / box / keypad plugin.

Identifiers per apk-ble-hunting/reports/nuki_passive.md.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nuki import NukiParser, NUKI_UUIDS


LOCK_ADV_UUID = "a92ee000-5501-11e4-916c-0800200c9a66"
LOCK_PAIRING_UUID = "a92ee100-5501-11e4-916c-0800200c9a66"
LOCK_KEYTURNER_UUID = "a92ee200-5501-11e4-916c-0800200c9a66"
LOCK_FIRMWARE_UUID = "a92eef00-5501-11e4-916c-0800200c9a66"
BRIDGE_UUID = "a92fe000-5501-11e4-916c-0800200c9a66"
FOB_USER_UUID = "a92be100-5501-11e4-916c-0800200c9a66"
BOX_UUID = "a92de000-5501-11e4-916c-0800200c9a66"
KEYPAD_UUID = "a92ce000-5501-11e4-916c-0800200c9a66"


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


def _register(registry):
    all_uuids = [u for u, _, _ in NUKI_UUIDS]

    @register_parser(
        name="nuki",
        service_uuid=all_uuids,
        description="Nuki",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(NukiParser):
        pass


class TestNukiConstants:
    def test_nine_uuids_defined(self):
        assert len(NUKI_UUIDS) == 9

    def test_all_uuids_share_suffix(self):
        for u, _, _ in NUKI_UUIDS:
            assert u.endswith("-5501-11e4-916c-0800200c9a66")


class TestNukiMatching:
    def test_matches_lock_advertising_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[LOCK_ADV_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_via_service_data(self):
        parser = NukiParser()
        ad = _make_ad(service_data={LOCK_ADV_UUID: b"\xDE\xAD\xBE\xEF"})
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "lock"

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["1234"])
        assert len(registry.match(ad)) == 0


class TestNukiProductFamilies:
    def _parse(self, **kwargs):
        parser = NukiParser()
        return parser.parse(_make_ad(**kwargs))

    def test_lock(self):
        result = self._parse(service_uuids=[LOCK_ADV_UUID])
        assert result.metadata["product_family"] == "lock"
        assert result.metadata["role"] == "advertising"
        assert result.device_class == "lock"

    def test_bridge(self):
        result = self._parse(service_uuids=[BRIDGE_UUID])
        assert result.metadata["product_family"] == "bridge"
        assert result.device_class == "bridge"

    def test_fob(self):
        result = self._parse(service_uuids=[FOB_USER_UUID])
        assert result.metadata["product_family"] == "fob"
        assert result.metadata["role"] == "user"
        assert result.device_class == "key"

    def test_box(self):
        result = self._parse(service_uuids=[BOX_UUID])
        assert result.metadata["product_family"] == "box"

    def test_keypad(self):
        result = self._parse(service_uuids=[KEYPAD_UUID])
        assert result.metadata["product_family"] == "keypad"
        assert result.device_class == "keypad"


class TestNukiRoles:
    def _parse(self, **kwargs):
        return NukiParser().parse(_make_ad(**kwargs))

    def test_keyturner_role(self):
        result = self._parse(service_uuids=[LOCK_KEYTURNER_UUID])
        assert result.metadata["role"] == "keyturner"

    def test_pairing_mode_flag(self):
        result = self._parse(service_uuids=[LOCK_ADV_UUID, LOCK_PAIRING_UUID])
        assert result.metadata["in_pairing_mode"] is True

    def test_firmware_update_flag(self):
        result = self._parse(service_uuids=[LOCK_FIRMWARE_UUID])
        assert result.metadata["in_firmware_update"] is True

    def test_no_pairing_flag_when_only_advertising(self):
        result = self._parse(service_uuids=[LOCK_ADV_UUID])
        assert "in_pairing_mode" not in result.metadata


class TestNukiParseFields:
    def test_parser_name(self):
        result = NukiParser().parse(_make_ad(service_uuids=[LOCK_ADV_UUID]))
        assert result.parser_name == "nuki"

    def test_beacon_type(self):
        result = NukiParser().parse(_make_ad(service_uuids=[LOCK_ADV_UUID]))
        assert result.beacon_type == "nuki"

    def test_identity_hash(self):
        ad = _make_ad(service_uuids=[LOCK_ADV_UUID], mac_address="11:22:33:44:55:66")
        result = NukiParser().parse(ad)
        expected = hashlib.sha256("nuki:11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_service_payload_extracted(self):
        ad = _make_ad(service_data={LOCK_ADV_UUID: b"\x01\x02\x03"})
        result = NukiParser().parse(ad)
        assert result.metadata["service_payload_hex"] == "010203"
