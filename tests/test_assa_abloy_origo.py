"""Tests for ASSA ABLOY / HID Global Origo Mobile Access plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.assa_abloy_origo import (
    AssaAbloyOrigoParser,
    HID_GLOBAL_COMPANY_ID,
    APPLE_COMPANY_ID,
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


def _register(registry):
    @register_parser(
        name="assa_abloy_origo",
        company_id=(HID_GLOBAL_COMPANY_ID, APPLE_COMPANY_ID),
        description="Origo",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(AssaAbloyOrigoParser):
        pass
    return _P


def _hid_mfr(version=1, n=0, profile=0, opening_mask=0x05, thresholds=(-40, -65)):
    """Build HID-Global mfr-data: CID 012E + payload."""
    cid = struct.pack("<H", HID_GLOBAL_COMPANY_ID)
    payload = bytes([
        0x01, 0x2E,                      # echoed mfr-id big-endian
        ((version & 0x0F) << 4) | (n & 0x0F),
    ])
    payload += bytes(n)                   # trigger block
    payload += bytes([profile, opening_mask])
    for t in thresholds:
        payload += bytes([t & 0xFF])
    return cid + payload


def _ibeacon_origo(deployment_code_hex="abcdef", major_minor=b"\xde\xad\xbe\xef"):
    """Build an iBeacon mfr-data with an Origo-shape proximity UUID."""
    cid = struct.pack("<H", APPLE_COMPANY_ID)
    # Construct UUID bytes in RFC4122 byte order matching `00009800-0000-1000-8000-00177A<code>`
    uuid_bytes = bytes.fromhex(
        "00009800" + "0000" + "1000" + "8000" + "00177a" + deployment_code_hex
    )
    payload = bytes([0x02, 0x15]) + uuid_bytes + major_minor + bytes([0xB5])
    return cid + payload


class TestOrigoMatching:
    def test_uuid_only_invocation_extracts_deployment_code(self):
        """Per-deployment UUIDs vary in low 24 bits and aren't enumerable, so
        registry matching happens via mfr-data CID. When parse() is invoked
        with only an Origo UUID in service_uuids, it still extracts the code."""
        ad = _make_ad(service_uuids=["00009800-0000-1000-8000-00177a123456"])
        result = AssaAbloyOrigoParser().parse(ad)
        assert result is not None
        assert result.metadata["deployment_code_hex"] == "123456"

    def test_matches_hid_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_hid_mfr())
        assert len(registry.match(ad)) == 1

    def test_matches_apple_cid_with_origo_ibeacon(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_ibeacon_origo())
        assert len(registry.match(ad)) == 1


class TestOrigoUuidParsing:
    def test_deployment_code_extracted(self):
        ad = _make_ad(service_uuids=["00009800-0000-1000-8000-00177aabcdef"])
        result = AssaAbloyOrigoParser().parse(ad)
        assert result.metadata["deployment_code_hex"] == "abcdef"


class TestHidMfrParsing:
    def test_opening_types_decoded(self):
        # bitmask 0x05 = bit 0 (PROXIMITY) + bit 2 (SEAMLESS)
        ad = _make_ad(manufacturer_data=_hid_mfr(opening_mask=0x05))
        result = AssaAbloyOrigoParser().parse(ad)
        assert "PROXIMITY" in result.metadata["opening_types"]
        assert "SEAMLESS" in result.metadata["opening_types"]
        assert result.metadata["opening_type_bitmask"] == 0x05

    def test_credential_unavailable_bit(self):
        ad = _make_ad(manufacturer_data=_hid_mfr(opening_mask=0x80))
        result = AssaAbloyOrigoParser().parse(ad)
        assert result.metadata["credential_unavailable"] is True

    def test_rssi_thresholds_signed(self):
        ad = _make_ad(manufacturer_data=_hid_mfr(thresholds=(-40, -65, -50)))
        result = AssaAbloyOrigoParser().parse(ad)
        assert result.metadata["rssi_threshold_seamless"] == -40
        assert result.metadata["rssi_threshold_proximity"] == -65
        assert result.metadata["rssi_threshold_motion"] == -50


class TestOrigoIBeacon:
    def test_ibeacon_decode(self):
        ad = _make_ad(manufacturer_data=_ibeacon_origo(
            deployment_code_hex="123456",
            major_minor=b"\xab\xcd\x12\x34",
        ))
        result = AssaAbloyOrigoParser().parse(ad)
        assert result.metadata["deployment_code_hex"] == "123456"
        assert result.metadata["ibeacon_major_minor_hex"] == "abcd1234"
        assert result.metadata["ibeacon_tx_power"] == -75
        assert result.metadata["role"] == "phone"

    def test_non_origo_ibeacon_returns_none(self):
        # iBeacon UUID that doesn't match the Origo template
        cid = struct.pack("<H", APPLE_COMPANY_ID)
        uuid_bytes = bytes.fromhex("0123456789abcdef0123456789abcdef")
        payload = bytes([0x02, 0x15]) + uuid_bytes + b"\x00\x00\x00\x00" + bytes([0xB5])
        ad = _make_ad(manufacturer_data=cid + payload)
        # Apple CID alone won't trigger the parser (correctly)
        assert AssaAbloyOrigoParser().parse(ad) is None


class TestOrigoIdentity:
    def test_identity_uses_major_minor(self):
        ad = _make_ad(manufacturer_data=_ibeacon_origo(
            major_minor=b"\xde\xad\xbe\xef",
        ))
        result = AssaAbloyOrigoParser().parse(ad)
        expected = hashlib.sha256(b"origo:phone:deadbeef").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_basics(self):
        ad = _make_ad(service_uuids=["00009800-0000-1000-8000-00177a000001"])
        result = AssaAbloyOrigoParser().parse(ad)
        assert result.parser_name == "assa_abloy_origo"
        assert result.device_class == "access_control"
