"""Tests for Chipolo tracker tag plugin.

Identifiers per apk-ble-hunting/reports/chipolo-net-v3_passive.md.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.chipolo import (
    ChipoloParser,
    CHIPOLO_COMPANY_ID,
    CHIPOLO_PROXIMITY_UUID,
    CHIPOLO_FMDN_PREFIX_A,
    CHIPOLO_FMDN_PREFIX_B,
)


SERVICE_UUIDS = ["fe33", "fe65", "fd44"]


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
    @register_parser(
        name="chipolo",
        company_id=CHIPOLO_COMPANY_ID,
        service_uuid=SERVICE_UUIDS,
        description="Chipolo",
        version="1.1.0",
        core=False,
        registry=registry,
    )
    class _P(ChipoloParser):
        pass

    return _P


class TestChipoloConstants:
    def test_proximity_uuid(self):
        assert CHIPOLO_PROXIMITY_UUID.lower() == "9ee14dfb-67f0-400f-86d1-4c2728b83f0f"

    def test_fmdn_prefixes_are_8_bytes(self):
        assert len(CHIPOLO_FMDN_PREFIX_A) == 8
        assert len(CHIPOLO_FMDN_PREFIX_B) == 8
        # From jx/a.java:25-26
        assert CHIPOLO_FMDN_PREFIX_A == bytes.fromhex("8dae5760d6b85941")
        assert CHIPOLO_FMDN_PREFIX_B == bytes.fromhex("8dae5760e3451d04")


class TestChipoloMatching:
    def test_match_legacy_fe33(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_data={"fe33": b"\x03"}, service_uuids=["fe33"])
        assert len(registry.match(ad)) == 1

    def test_match_current_fe65(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_data={"fe65": b"\x00\x01\x02"}, service_uuids=["fe65"])
        assert len(registry.match(ad)) == 1

    def test_match_fmdn_fd44(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(
            service_data={"fd44": CHIPOLO_FMDN_PREFIX_A + b"\xAA\xBB"},
            service_uuids=["fd44"],
        )
        assert len(registry.match(ad)) == 1

    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        mfr_data = struct.pack("<H", CHIPOLO_COMPANY_ID) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1


class TestChipoloVariantTagging:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_variant_legacy_from_fe33(self):
        result = self._parse(service_data={"fe33": b"\x04"})
        assert result.metadata["variant"] == "legacy"
        assert result.metadata["color_code"] == 4

    def test_variant_current_from_fe65(self):
        result = self._parse(service_data={"fe65": b"\x11\x22\x33"})
        assert result.metadata["variant"] == "current"

    def test_variant_fmdn_a_from_fd44_prefix_a(self):
        payload = CHIPOLO_FMDN_PREFIX_A + b"\xDE\xAD\xBE\xEF"
        result = self._parse(service_data={"fd44": payload})
        assert result.metadata["variant"] == "fmdn_a"

    def test_variant_fmdn_b_from_fd44_prefix_b(self):
        payload = CHIPOLO_FMDN_PREFIX_B + b"\x01\x02"
        result = self._parse(service_data={"fd44": payload})
        assert result.metadata["variant"] == "fmdn_b"

    def test_variant_fmdn_other_from_fd44_unknown_prefix(self):
        # FD44 is used by multiple Fast Pair / Find My Device vendors.
        # Without a recognised Chipolo prefix, don't claim fmdn_a/_b.
        payload = bytes(16)
        result = self._parse(service_data={"fd44": payload})
        assert result.metadata["variant"] == "fmdn"

    def test_color_only_applied_for_legacy_fe33(self):
        # FE65/FD44 payloads shouldn't get Gray-from-byte-0 misinterpretation.
        result = self._parse(service_data={"fe65": b"\x00\xFF"})
        assert "color_code" not in result.metadata

    def test_fmdn_rotating_id_extracted(self):
        rotating = b"\xDE\xAD\xBE\xEF\x11\x22\x33\x44"
        payload = CHIPOLO_FMDN_PREFIX_A + rotating
        result = self._parse(service_data={"fd44": payload})
        assert result.metadata["fmdn_rotating_id_hex"] == rotating.hex()


class TestChipoloLegacyBehavior:
    """Keep the original color + identity-hash + device_class tests intact."""

    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_color_lookup_gray(self):
        result = self._parse(service_data={"fe33": b"\x00"})
        assert result.metadata["color"] == "Gray"

    def test_color_lookup_pink(self):
        result = self._parse(service_data={"fe33": b"\x09"})
        assert result.metadata["color"] == "Pink"

    def test_identity_hash(self):
        mfr_data = struct.pack("<H", CHIPOLO_COMPANY_ID) + b"\x01"
        result = self._parse(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        expected = hashlib.sha256("11:22:33:44:55:66:chipolo".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self):
        mfr_data = struct.pack("<H", CHIPOLO_COMPANY_ID) + b"\x01"
        result = self._parse(manufacturer_data=mfr_data)
        assert result.device_class == "tracker"
